"""
Sentiment scoring.
Deployed build uses OpenAI (gpt-4o-mini) for portability — no torch/transformers,
so the container stays light and starts fast. Returns the same shape the rest of
the system expects: {"label": str, "score": float} where score is -1..1.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


def _openai_sentiment(text: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    text = (text or "").strip()
    if not text:
        return {"label": "neutral", "score": 0.0}

    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{
                "role": "user",
                "content": (
                    "Score the financial sentiment of the text below. "
                    "Respond ONLY with JSON: "
                    '{"label": "positive|negative|neutral", "score": <float -1 to 1>}. '
                    "Negative = bearish, positive = bullish.\n\n"
                    f"Text: {text[:1500]}"
                ),
            }],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=40,
        )
        data = json.loads(resp.choices[0].message.content)
        label = str(data.get("label", "neutral")).lower()
        score = float(data.get("score", 0.0))
        score = max(-1.0, min(1.0, score))
        return {"label": label, "score": score}
    except Exception as e:
        logger.warning(f"[Sentiment] OpenAI scoring failed: {e}")
        return {"label": "neutral", "score": 0.0}


def score_sentiment(text: str) -> dict:
    """Single-text sentiment. Returns {'label': str, 'score': float in -1..1}."""
    return _openai_sentiment(text)


def batch_score(texts: list) -> list:
    """Score a list of texts. (Social agent is dropped, but kept for compatibility.)"""
    return [_openai_sentiment(t) for t in texts]