"""Shared sentiment scoring configuration (Market-Sentiment methodology)."""

SENTIMENT_RANGES = {
    "weak": (0.15, 0.39),
    "moderate": (0.4, 0.69),
    "strong": (0.7, 1.0),
}

SENTIMENT_WEIGHTS = {
    "weak": 1,
    "moderate": 2,
    "strong": 3,
}

BAYESIAN_EXTRA_VALUES = 100

SENTIMENT_POSITIVE_THRESHOLD = SENTIMENT_RANGES["weak"][0]
SENTIMENT_RANGES_MODERATE = SENTIMENT_RANGES["moderate"][0]

BUCKET_LABELS = [
    "weak_positive",
    "moderate_positive",
    "strong_positive",
    "weak_negative",
    "moderate_negative",
    "strong_negative",
]


def bucket_requests() -> list[tuple[str, float, float]]:
    """Return (label, sentiment_gte, sentiment_lte) triples for all buckets."""
    result = []
    for strength, (low, high) in SENTIMENT_RANGES.items():
        result.append((f"{strength}_positive", low, high))
    for strength, (low, high) in SENTIMENT_RANGES.items():
        result.append((f"{strength}_negative", -high, -low))
    return result


def adjusted_sentiment_score(counts: dict) -> float:
    """Bayesian-normalised sentiment score in [-1, 1] from bucket counts."""
    raw = 0
    weighted_total = 0
    for strength, weight in SENTIMENT_WEIGHTS.items():
        positives = counts.get(f"{strength}_positive", 0)
        negatives = counts.get(f"{strength}_negative", 0)
        raw += (positives - negatives) * weight
        weighted_total += (positives + negatives) * weight

    denominator = weighted_total + BAYESIAN_EXTRA_VALUES
    if denominator <= 0:
        return 0.0
    return raw / denominator


def classify(score: float | None) -> str:
    """Classify a sentiment score using the shared bucket boundaries."""
    if score is None:
        return "No Coverage"
    weak = SENTIMENT_POSITIVE_THRESHOLD
    moderate = SENTIMENT_RANGES_MODERATE
    if score >= moderate:
        return "Bullish"
    if score >= weak:
        return "Positive"
    if score <= -moderate:
        return "Bearish"
    if score <= -weak:
        return "Negative"
    return "Neutral"
