#!/usr/bin/env python3
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from models import ScoreReq, ScoreResp
from scoring.behavior import score_behavior
from scoring.structure import score_structure
from scoring.institutional import score_institutional
from scoring.sentiment import score_sentiment
from scoring.execution import score_execution_validity
from feeds.news import pull_news_summary
from feeds.social import pull_social_summary
from feeds.gamma import gamma_note
from utils import compute_penalties, grade_from_composite, json_logger

app = FastAPI(title="ODTE Sidecar", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}

@app.post("/score", response_model=ScoreResp)
def score(req: ScoreReq):
    # Step 1: hypothesis (rules-only for now; you can swap with LLM later)
    hypothesis = build_hypothesis(req)

    # Step 2: compute sub-scores in 0..1
    s_behavior = score_behavior(req)
    s_structure = score_structure(req)
    s_inst     = score_institutional(req)
    s_sent     = score_sentiment(req)
    s_exec     = score_execution_validity(req)

    penalties = compute_penalties(req)

    composite = (
        0.30 * s_behavior +
        0.25 * s_structure +
        0.20 * s_inst +
        0.15 * s_sent +
        0.10 * s_exec
        - sum(penalties.values())
    )
    composite = max(0.0, min(1.0, composite))
    grade = grade_from_composite(composite)

    evidence = {
        "news_summary": pull_news_summary(req.symbol),
        "social_summary": pull_social_summary(req.symbol),
        "gamma_note": gamma_note(req.symbol)
    }

    resp = ScoreResp(
        hypothesis=hypothesis,
        scores={
            "behavior": round(s_behavior, 3),
            "structure": round(s_structure, 3),
            "institutional": round(s_inst, 3),
            "sentiment": round(s_sent, 3),
            "execution_validity": round(s_exec, 3),
        },
        penalties={k: round(v, 3) for k, v in penalties.items()},
        composite=round(composite, 3),
        grade=grade,
        evidence=evidence
    )

    # Log request + response for audit
    try:
        json_logger("score", {"request": req.model_dump(), "response": resp.model_dump()})
    except Exception:
        pass

    return resp

def build_hypothesis(req: ScoreReq) -> str:
    pc = req.price_context or {}
    struct = req.structure or {}
    last = pc.get("last")
    vwap = pc.get("vwap")
    or_high = pc.get("or_high")
    or_low = pc.get("or_low")
    breakout = struct.get("breakout_state")
    dir_hint = ""
    if breakout == "above_premarket_high" or (last is not None and or_high is not None and last > or_high):
        dir_hint = "call-side favored"
    elif breakout == "below_premarket_low" or (last is not None and or_low is not None and last < or_low):
        dir_hint = "put-side favored"
    else:
        dir_hint = "range-bound risk; patience"

    parts = []
    if last is not None and vwap is not None:
        parts.append(f"{req.symbol} trading {('above' if last>vwap else 'below')} VWAP")
    if breakout:
        parts.append(f"breakout state: {breakout}")
    return "; ".join(parts) + f" — {dir_hint}."

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="127.0.0.1", port=port)
