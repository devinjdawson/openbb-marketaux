"""Marketaux news feed widgets."""

from fastapi import APIRouter

import core
from services import sentiment as sentiment_service
from services.marketaux import MarketauxError, client

router = APIRouter()

SENTIMENT_OPTIONS = [
    {"label": "All", "value": "all"},
    {"label": "Positive", "value": "positive"},
    {"label": "Negative", "value": "negative"},
]

LANGUAGE_OPTIONS = [
    {"label": "English", "value": "en"},
    {"label": "Spanish", "value": "es"},
    {"label": "French", "value": "fr"},
    {"label": "German", "value": "de"},
    {"label": "Chinese", "value": "zh"},
    {"label": "Japanese", "value": "ja"},
]


def transform_article(article: dict) -> dict:
    excerpt = article.get("description") or article.get("snippet") or ""
    return {
        "title": article.get("title"),
        "date": article.get("published_at"),
        "author": article.get("source"),
        "excerpt": excerpt,
        "body": article.get("snippet") or excerpt,
        "url": article.get("url"),
        "image_url": article.get("image_url"),
        "sentiment": next(
            (e.get("sentiment_score") for e in article.get("entities", [])),
            None,
        ),
    }


def sentiment_filter(sentiment: str) -> dict:
    if sentiment == "positive":
        return {"sentiment_gte": core.SENTIMENT_POSITIVE_THRESHOLD}
    if sentiment == "negative":
        return {"sentiment_lte": core.SENTIMENT_NEGATIVE_THRESHOLD}
    return {}


@core.register_widget({
    "name": "Market News",
    "description": "Global financial news from Marketaux with search and sentiment filters",
    "category": "Marketaux News",
    "type": "newsfeed",
    "endpoint": "news_market",
    "gridData": {"w": 20, "h": 16},
    "source": ["Marketaux"],
    "params": [
        [
            {
                "paramName": "search",
                "label": "Search",
                "description": "Free-text search over titles and bodies ("
                               '+and ", -not, |or, "phrase", prefix*)',
                "type": "text",
                "value": "",
            },
            {
                "paramName": "sentiment",
                "label": "Sentiment",
                "description": "Filter articles by entity sentiment",
                "type": "text",
                "value": "all",
                "options": SENTIMENT_OPTIONS,
            },
        ],
        [
            {
                "paramName": "language",
                "label": "Language",
                "description": "Language of the news sources",
                "type": "text",
                "value": "en",
                "options": LANGUAGE_OPTIONS,
            },
            {
                "paramName": "limit",
                "label": "Limit",
                "description": "Number of articles to return",
                "type": "number",
                "value": 20,
                "min": 1,
                "max": 100,
            },
        ],
    ],
})
@router.get("/news_market")
def news_market(search: str = "", sentiment: str = "all",
                language: str = "en", limit: int = 20):
    """Latest global financial news from Marketaux."""

    def fetch():
        params = {
            "language": language,
            "limit": limit,
            "group_similar": "true",
        }
        if search:
            params["search"] = search
        params.update(sentiment_filter(sentiment))
        return client.news_all(**params)

    try:
        payload = core.cache.get_or_set(
            f"news_market:{search}:{sentiment}:{language}:{limit}",
            fetch, core.CACHE_TTL_NEWS,
        )
        return [transform_article(a) for a in payload.get("data", [])]
    except MarketauxError as exc:
        return core.error_response(exc.status_code, exc.code, exc.message)


@core.register_widget({
    "name": "Symbol News",
    "description": "Marketaux news identified for a specific symbol, linked to Group 1",
    "category": "Marketaux News",
    "type": "newsfeed",
    "endpoint": "news_symbol",
    "gridData": {"w": 20, "h": 16},
    "source": ["Marketaux"],
    "params": [
        [
            {
                "paramName": "symbol",
                "label": "Symbol",
                "description": "Entity symbol to fetch news for",
                "type": "endpoint",
                "optionsEndpoint": "/symbol_options",
                "value": "AAPL",
            },
            {
                "paramName": "days",
                "label": "Days",
                "description": "Lookback window in days",
                "type": "number",
                "value": core.SENTIMENT_DAYS,
                "min": 1,
                "max": 90,
            },
        ],
        [
            {
                "paramName": "limit",
                "label": "Limit",
                "description": "Number of articles to return",
                "type": "number",
                "value": 20,
                "min": 1,
                "max": 100,
            },
        ],
    ],
})
@router.get("/news_symbol")
def news_symbol(symbol: str = "AAPL", days: int = core.SENTIMENT_DAYS,
                limit: int = 20):
    """News for a single symbol, entities filtered to the requested symbol."""

    def fetch():
        return client.news_all(
            symbols=symbol.upper(),
            filter_entities="true",
            must_have_entities="true",
            sort="entity_match_score",
            published_after=sentiment_service.published_after(days),
            language="en",
            limit=limit,
        )

    try:
        payload = core.cache.get_or_set(
            f"news_symbol:{symbol.upper()}:{days}:{limit}",
            fetch, core.CACHE_TTL_NEWS,
        )
        return [transform_article(a) for a in payload.get("data", [])]
    except MarketauxError as exc:
        return core.error_response(exc.status_code, exc.code, exc.message)
