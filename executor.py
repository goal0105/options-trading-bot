import requests
import json
import logging

class BaseExecutor:
    def submit_bracket(self, order_payload: dict):
        raise NotImplementedError

class MockExecutor(BaseExecutor):
    def submit_bracket(self, order_payload: dict):
        logging.info("MOCK ORDER SUBMIT: %s", json.dumps(order_payload, indent=2))
        # return simulated order id and status
        return {"status": "simulated", "order_id": "mock-123"}

class AlpacaExecutor(BaseExecutor):
    def __init__(self, key, secret, base_url="https://paper-api.alpaca.markets"):
        self.key = key
        self.secret = secret
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Content-Type": "application/json"
        })

    def submit_bracket(self, order_payload: dict):
        # build an Alpaca bracket order payload for options or stock.
        # Adapt this to your provider / options API.
        # For simplicity we submit a stock bracket order example.
        url = f"{self.base_url}/v2/orders"
        resp = self.session.post(url, json=order_payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

def build_bracket_order(symbol: str, qty: int, side: str, limit_price: float, take_profit: float, stop_price: float):
    # This structure is compatible with Alpaca for equity bracket orders.
    return {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "limit",
        "time_in_force": "day",
        "limit_price": str(limit_price),
        "order_class": "bracket",
        "take_profit": {"limit_price": str(take_profit)},
        "stop_loss": {"stop_price": str(stop_price)}
    }