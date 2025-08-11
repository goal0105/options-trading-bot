# main.py
import asyncio
import yaml
import logging
import math
from data_client import MockDataClient, AlpacaDataClient
from indicators import percent_change_from_first_open_to_last_close, average_volume, atr_simple, gap_fill_pct, last_above_20ma
from rubric import grade_packet_for_trade
from executor import MockExecutor, AlpacaExecutor, build_bracket_order
from ai_bridge import format_json_for_llm, call_llm_for_sentiment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def load_config(path="config_example.yaml"):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def prepare_data_client(cfg):
    t = cfg.get('data_provider', {}).get('type', 'mock')
    if t == 'mock':
        return MockDataClient()
    if t == 'alpaca':
        key = cfg['data_provider']['api_key']
        secret = cfg['data_provider'].get('api_secret', '')
        return AlpacaDataClient(key, secret)
    # add polygon or other clients here
    return MockDataClient()

def prepare_executor(cfg):
    prov = cfg.get('execution', {}).get('provider', 'mock')
    if prov == 'alpaca':
        e = cfg['execution']
        return AlpacaExecutor(e['api_key'], e['api_secret'], e.get('base_url'))
    return MockExecutor()

def size_by_grade(cfg, account_value, grade):
    s = cfg.get('sizing', {})
    if grade == "A+":
        pct = s.get('grade_A_plus', 0.05)
    elif grade == "A":
        pct = s.get('grade_A', 0.03)
    elif grade == "B":
        pct = s.get('grade_B', 0.01)
    else:
        pct = s.get('max_risk_per_trade_pct', 0.01)
    # simple fixed-money sizing based on pct of account value as risk dollars
    return pct

async def scan_and_trade(cfg):
    data_client = prepare_data_client(cfg)
    executor = prepare_executor(cfg)
    symbols = cfg.get('symbols', ['SPY','QQQ','TSLA'])
    lookback = cfg.get('scan', {}).get('lookback_bars', 18)
    interval = cfg.get('scan', {}).get('scan_interval_seconds', 30)

    account_value = 100000  # placeholder; ideally fetch from execution provider

    while True:
        for sym in symbols:
            try:
                df = data_client.get_minutes(sym, limit=lookback)
                if df is None or len(df) < 6:
                    logging.debug("not enough data for %s", sym)
                    continue

                pct = percent_change_from_first_open_to_last_close(df)
                avg_v = average_volume(df)
                atr = atr_simple(df)
                gap_pct = gap_fill_pct(df)
                above20 = last_above_20ma(df)

                # simple breakout/hold heuristics
                last_close = float(df['c'].iloc[-1])
                prev_close = float(df['c'].iloc[-2])
                breakout = last_close > prev_close and (pct > 0.2)
                hold_2bars = False
                if len(df) >= 3:
                    # check that last 2 bars are above previous breakout level
                    hold_2bars = df['c'].iloc[-1] > df['c'].iloc[-3] and df['c'].iloc[-2] > df['c'].iloc[-3]

                metrics = {
                    'percent_change': pct,
                    'avg_volume': avg_v,
                    'atr': atr,
                    'gap_pct': gap_pct,
                    'last_above_20ma': above20,
                    'breakout_confirmed': breakout,
                    'hold_2bars': hold_2bars,
                    'v_last': int(df['v'].iloc[-1]),
                    'during_allowed_hours': True,  # implement time checks if desired
                    'gex_flat_or_pos': False
                }

                # call AI bridge to enrich sentiment
                fmt = format_json_for_llm(sym, metrics, [])
                llm = call_llm_for_sentiment(fmt)
                metrics['sentiment_score'] = llm.get('sentiment_score', 0.5)

                grade_packet = grade_packet_for_trade(sym, metrics, cfg.get('rubric_weights'))
                logging.info("GRADE %s %s %.3f %s", sym, grade_packet['grade'], grade_packet['composite'], grade_packet['subscores'])

                # Only place orders for A+ or A (per your rule)
                if grade_packet['grade'] in ("A+","A"):
                    # determine size
                    pct_risk = size_by_grade(cfg, account_value, grade_packet['grade'])
                    qty_target = math.floor((account_value * pct_risk) / max(1.0, last_close))
                    if qty_target <= 0:
                        logging.info("quantity computed 0 for %s; skipping", sym)
                        continue

                    # compute bracket levels (simple)
                    limit_price = round(last_close, 2)
                    stop_price = round(last_close - (metrics['atr'] * 1.0), 2)  # stop = 1*ATR below
                    take_profit = round(last_close + (metrics['atr'] * 1.5), 2)  # TP = 1.5*ATR

                    order_payload = build_bracket_order(sym, qty_target, "buy", limit_price, take_profit, stop_price)
                    logging.info("Submitting bracket order for %s: %s", sym, order_payload)
                    res = executor.submit_bracket(order_payload)
                    logging.info("Order result: %s", res)
                else:
                    logging.debug("No trade for %s — grade %s", sym, grade_packet['grade'])

            except Exception as e:
                logging.exception("Error scanning %s: %s", sym, e)

        await asyncio.sleep(interval)

def main():
    cfg = load_config("config_example.yaml")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(scan_and_trade(cfg))
    except KeyboardInterrupt:
        logging.info("Stopped by user")

if __name__ == "__main__":
    main()
