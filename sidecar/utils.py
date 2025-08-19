import os
import json
import time
import pathlib
from typing import Dict, Any
from models import ScoreReq

LOG_DIR = pathlib.Path(os.getenv("LOG_DIR", "/tmp/odte-sidecar/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

def json_logger(event: str, payload: Dict[str, Any]) -> None:
    """
    Write a small JSON file per event for auditing/debugging.
    Non-blocking: swallow IO errors.
    """
    try:
        ts = int(time.time() * 1000)
        path = LOG_DIR / f"{ts}_{event}.json"
        # ensure JSON-serializable: try to dump directly; if fails, string-ify
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
    except Exception:
        # intentionally silent for reliability in production
        return

def compute_penalties(req: ScoreReq) -> Dict[str, float]:
    """
    Compute penalties based on risk/technical context.
    Return a dict of penalty_name -> penalty_value (0..1).
    Tune thresholds to your data.
    """
    penalties: Dict[str, float] = {}

    # Low average volume penalty (example threshold)
    vol = None
    if isinstance(req.technicals, dict):
        vol = req.technicals.get("avg_volume_10") or req.technicals.get("avg_volume")

    if vol is not None:
        try:
            if float(vol) < 1e5:
                penalties["low_volume"] = 0.30
        except Exception:
            pass

    # Earnings proximity penalty (expects boolean flag under risk_context)
    if req.risk_context.get("earnings_within_72h"):
        penalties["earnings_72h"] = 0.20

    # Add other penalties as needed (thin option chain, low open interest, etc.)
    if req.risk_context.get("thin_option_chain"):
        penalties["thin_chain"] = 0.10

    # Cap total penalty at 0.8 to avoid negative composites
    total = sum(penalties.values())
    if total > 0.8:
        # scale down proportionally
        factor = 0.8 / total
        for k in list(penalties.keys()):
            penalties[k] = round(penalties[k] * factor, 4)

    return penalties

def grade_from_composite(c: float) -> str:
    """
    Map composite (0..1) to grade strings.
    """
    if c >= 0.90:
        return "A+"
    if c >= 0.85:
        return "A"
    if c >= 0.70:
        return "B"
    if c >= 0.60:
        return "C"
    return "D"
