import time
import logging
from typing import Dict

def format_json_for_llm(ticker: str, tech: Dict, news_snippets: list) -> dict:
    return {
        "symbol": ticker,
        "technical": tech,
        "news": news_snippets,
        "ask": "give me a sentiment score (0-1) and short market hypothesis"
    }

def call_llm_for_sentiment(formatted_json: dict) -> Dict:
    # Placeholder synchronous fake LLM response. Replace with real OpenAI client.
    time.sleep(0.2)
    # naive heuristic:
    comp = formatted_json["technical"]
    sentiment_score = 0.5
    if comp.get('percent_change', 0) > 0 and comp.get('v_last', 0) > comp.get('avg_volume', 1):
        sentiment_score = 0.8
    return {"sentiment_score": sentiment_score, "thesis": "Market bias supportive of trade."}
