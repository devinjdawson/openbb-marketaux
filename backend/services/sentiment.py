"""Sentiment scoring built on Marketaux data.

Ports the bucketed Bayesian approach from the Market-Sentiment reference app:
articles are counted in six sentiment buckets (weak/moderate/strong x
positive/negative) and normalised with a Bayesian prior so symbols with
little news coverage are not over-ranked.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import core
from services.marketaux import client

BUCKET_LABELS = [
    "weak_positive",
    "moderate_positive",
    "strong_positive",
    "weak_negative",
    "moderate_negative",
    "strong_negative",
]

BUCKET_COLORS = {
    "weak_positive": "#86EFAC",
    "moderate_positive": "#4ADE80",
    "strong_positive": "#16A34A",
    "weak_negative": "#FCA5A5",
    "moderate_negative": "#F87171",
    "strong_negative": "#DC2626",
}


def published_after(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M")


def bucket_requests() -> list:
    """Return (label, sentiment_gte, sentiment_lte) triples for all six buckets."""
    requests = []
    for strength, (low, high) in core.SENTIMENT_RANGES.items():
        requests.append((f"{strength}_positive", low, high))
    for strength, (low, high) in core.SENTIMENT_RANGES.items():
        requests.append((f"{strength}_negative", -high, -low))
    return requests


def fetch_bucket_data(symbols: str = "", days: int = core.SENTIMENT_DAYS,
                      language: str = "en", articles_per_bucket: int = 3,
                      api_token: str = "") -> dict:
    """Count articles per sentiment bucket for the given symbols.

    Costs six Marketaux requests per call (one per bucket), issued in
    parallel since the buckets are independent.
    """

    def request_bucket(item):
        label, gte, lte = item
        params = {
            "sentiment_gte": gte,
            "sentiment_lte": lte,
            "published_after": published_after(days),
            "language": language,
            "limit": articles_per_bucket,
        }
        if symbols:
            params["symbols"] = symbols
            params["filter_entities"] = "true"
            params["must_have_entities"] = "true"

        payload = client.news_all(api_token=api_token, **params)
        return (
            label,
            payload.get("meta", {}).get("found", 0),
            payload.get("data", []),
        )

    counts = {}
    articles = {}

    with ThreadPoolExecutor(max_workers=len(BUCKET_LABELS)) as pool:
        for label, found, bucket_articles in pool.map(request_bucket, bucket_requests()):
            counts[label] = found
            articles[label] = bucket_articles

    return {"counts": counts, "articles": articles}


def adjusted_sentiment_score(counts: dict) -> float:
    """Bayesian-normalised sentiment score in [-1, 1] from bucket counts."""
    weights = core.SENTIMENT_WEIGHTS

    raw = 0
    weighted_total = 0
    for strength, weight in weights.items():
        positives = counts.get(f"{strength}_positive", 0)
        negatives = counts.get(f"{strength}_negative", 0)
        raw += (positives - negatives) * weight
        weighted_total += (positives + negatives) * weight

    denominator = weighted_total + core.BAYESIAN_EXTRA_VALUES
    if denominator <= 0:
        return 0.0
    return raw / denominator


def classify(score: float) -> str:
    """Classify a sentiment score using the shared bucket boundaries."""
    weak = core.SENTIMENT_POSITIVE_THRESHOLD
    moderate = core.SENTIMENT_RANGES["moderate"][0]
    if score >= moderate:
        return "Bullish"
    if score >= weak:
        return "Positive"
    if score <= -moderate:
        return "Bearish"
    if score <= -weak:
        return "Negative"
    return "Neutral"


def symbol_article_stats(symbol: str, days: int = core.SENTIMENT_DAYS,
                         language: str = "en", limit: int = 100,
                         api_token: str = "") -> dict:
    """Sentiment stats for one symbol from a single news request."""
    payload = client.news_all(
        api_token=api_token,
        symbols=symbol,
        filter_entities="true",
        must_have_entities="true",
        sort="entity_match_score",
        published_after=published_after(days),
        language=language,
        limit=limit,
    )

    articles = payload.get("data", [])
    scores = []
    positive = negative = neutral = 0

    for article in articles:
        for entity in article.get("entities", []):
            if entity.get("symbol", "").upper() != symbol.upper():
                continue
            score = entity.get("sentiment_score")
            if score is None:
                continue
            scores.append(score)
            if score > 0:
                positive += 1
            elif score < 0:
                negative += 1
            else:
                neutral += 1

    avg_sentiment = round(sum(scores) / len(scores), 4) if scores else None
    return {
        "symbol": symbol,
        "total_articles": payload.get("meta", {}).get("found", 0),
        "analyzed_articles": len(articles),
        "avg_sentiment": avg_sentiment,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "classification": classify(avg_sentiment) if avg_sentiment is not None else "No Coverage",
        "headline": articles[0]["title"] if articles else "",
        "headline_url": articles[0].get("url", "") if articles else "",
        "headline_sentiment": next(
            (e.get("sentiment_score") for e in articles[0].get("entities", [])
             if e.get("symbol", "").upper() == symbol.upper()),
            None,
        ) if articles else None,
    }
