"""
FinBERT — financial-domain sentiment classifier.
Model: ProsusAI/finbert (3 labels: positive, negative, neutral)
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_pipeline():
    """Lazy-load FinBERT pipeline (cached after first call)."""
    from transformers import pipeline
    logger.info("[FinBERT] Loading model: ProsusAI/finbert")
    return pipeline(
        "sentiment-analysis",
        model="ProsusAI/finbert",
        truncation=True,
        max_length=512,
    )


def score_sentiment(text: str) -> dict:
    """
    Returns: {label: 'positive'|'negative'|'neutral', score: float in [-1,1]}
    """
    if not text or not text.strip():
        return {"label": "neutral", "score": 0.0}

    try:
        pipe = _get_pipeline()
        result = pipe(text[:512])[0]
        label = result["label"].lower()
        raw_score = result["score"]

        # Normalize to [-1, 1]
        if label == "positive":
            normalized = raw_score
        elif label == "negative":
            normalized = -raw_score
        else:
            normalized = 0.0

        return {"label": label, "score": normalized}

    except Exception as e:
        logger.warning(f"[FinBERT] Failed: {e}")
        return {"label": "neutral", "score": 0.0}


def batch_score(texts: list) -> list:
    """Score a batch of texts in one pass (faster)."""
    if not texts:
        return []
    try:
        pipe = _get_pipeline()
        results = pipe([t[:512] for t in texts])
        normalized = []
        for r in results:
            label = r["label"].lower()
            score = r["score"] if label == "positive" else (-r["score"] if label == "negative" else 0.0)
            normalized.append({"label": label, "score": score})
        return normalized
    except Exception as e:
        logger.warning(f"[FinBERT] Batch failed: {e}")
        return [{"label": "neutral", "score": 0.0}] * len(texts)
