from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ScoreReq(BaseModel):
    """
    Request payload from NinjaTrader (or any caller) to the sidecar /score endpoint.
    Keep fields permissive: callers may send extra keys in price_context / structure etc.
    """
    timestamp: str
    symbol: str
    price_context: Dict[str, float] = Field(default_factory=dict)
    structure: Dict[str, Any] = Field(default_factory=dict)
    technicals: Dict[str, float] = Field(default_factory=dict)
    session_time_ok: bool = True
    risk_context: Dict[str, Any] = Field(default_factory=dict)

class ScoreResp(BaseModel):
    """
    Response back to NinjaTrader:
      - hypothesis: short human-readable hypothesis string
      - scores: normalized sub-scores (0..1)
      - penalties: applied penalty values (0..1)
      - composite: combined score (0..1)
      - grade: mapped grade string (A+, A, B, ...)
      - evidence: small text blobs (news/social/gamma)
    """
    hypothesis: str
    scores: Dict[str, float]
    penalties: Dict[str, float]
    composite: float
    grade: str
    evidence: Dict[str, str] = Field(default_factory=dict)
