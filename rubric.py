from typing import Dict
import math

DEFAULT_WEIGHTS = {
    "behavior": 0.30,
    "structure": 0.25,
    "institutional": 0.20,
    "sentiment": 0.15,
    "execution": 0.10
}

GRADE_THRESHOLDS = [
    (0.85, "A+"),
    (0.75, "A"),
    (0.60, "B"),
    (0.40, "C"),
    (0.0,  "F")
]

def clamp01(x):
    return max(0.0, min(1.0, x))

def score_from_tech(tech_metrics: Dict) -> Dict:
    """
    tech_metrics expected keys:
      percent_change, avg_volume, atr, gap_fill, last_above_20ma, breakout_confirmed (bool), hold_2bars (bool)
    Returns per-category sub-scores in 0..1
    """
    # Behaviour (momentum + percent change + ATR)
    pct = abs(tech_metrics.get('percent_change', 0))
    # example mapping: larger pct -> higher behavior (up to 5% maps to 1.0)
    behavior = clamp01(min(pct / 5.0, 1.0))

    # Structure: breakout confirmation, 20MA breach, hold 2 bars
    structure = 0.0
    if tech_metrics.get('breakout_confirmed'):
        structure += 0.5
    if tech_metrics.get('last_above_20ma'):
        structure += 0.25
    if tech_metrics.get('hold_2bars'):
        structure += 0.25
    structure = clamp01(structure)

    # Institutional: volume spike relative to avg
    v = tech_metrics.get('v_last', 0)
    avg_v = tech_metrics.get('avg_volume', 1)
    inst = 0.0
    if avg_v > 0:
        ratio = v / avg_v
        inst = clamp01(min(ratio / 2.0, 1.0))  # 2x avg -> 1.0
    # penalize if dark pool prints flagged (placeholder)
    if tech_metrics.get('dark_pool_flag'):
        inst = max(0.0, inst - 0.3)

    # Sentiment: rely on external AI module or simple heuristic (placeholder)
    sentiment = clamp01(tech_metrics.get('sentiment_score', 0.5))

    # Execution validity: time windows, GEX check (placeholder booleans)
    exec_valid = 1.0
    if not tech_metrics.get('during_allowed_hours', True):
        exec_valid = 0.0
    if tech_metrics.get('gex_flat_or_pos', False):
        exec_valid = 0.0

    return {
        "behavior": behavior,
        "structure": structure,
        "institutional": inst,
        "sentiment": sentiment,
        "execution": exec_valid
    }

def combine_scores(subscores: Dict, weights: Dict = None) -> Dict:
    if weights is None:
        weights = DEFAULT_WEIGHTS
    composite = 0.0
    for k, w in weights.items():
        composite += subscores.get(k, 0.0) * w
    return {"composite": composite, "components": subscores}

def grade_from_score(score: float) -> str:
    for thresh, grade in GRADE_THRESHOLDS:
        if score >= thresh:
            return grade
    return "F"

def grade_packet_for_trade(symbol: str, metrics: Dict, weights: Dict = None) -> Dict:
    subs = score_from_tech(metrics)
    combined = combine_scores(subs, weights)
    composite = combined['composite']
    grade = grade_from_score(composite)
    return {
        "symbol": symbol,
        "subscores": subs,
        "composite": composite,
        "grade": grade,
        "components": combined['components']
    }