"""Marketaux Symbol Sentiment Summary Model."""

# pylint: disable=unused-argument

from datetime import date as dateType
from datetime import datetime, timedelta, timezone
from typing import Any

from openbb_core.app.model.abstract.error import OpenBBError
from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from openbb_core.provider.utils.errors import EmptyDataError
from openbb_marketaux.utils.dates import parse_datetime
from openbb_marketaux.utils.helpers import (
    get_token,
    marketaux_get,
    split_symbols,
)
from openbb_marketaux.utils.sentiment import classify
from pydantic import Field, field_validator


class MarketauxSentimentSummaryQueryParams(QueryParams):
    """Marketaux Sentiment Summary Query.

    Aggregates entity sentiment from recent news articles, per symbol.
    Costs one Marketaux API request per symbol.
    """

    symbol: str = Field(
        description="Comma separated list of symbols (e.g. `AAPL,TSLA,NVDA`)."
    )
    start_date: dateType | None = Field(
        default=None,
        description="Start of the lookback window. Defaults to 7 days ago.",
    )
    language: str | None = Field(
        default="en", description="Comma separated list of languages."
    )
    limit: int | None = Field(
        default=100,
        description="Maximum number of articles analysed per symbol.",
    )

    @field_validator("start_date", mode="before")
    @classmethod
    def start_date_validate(cls, v) -> dateType:
        """Default to 7 days ago."""
        if not v:
            v = datetime.now(timezone.utc) - timedelta(days=7)
        return v


class MarketauxSentimentSummaryData(Data):
    """Marketaux Sentiment Summary Data."""

    symbol: str = Field(description="The entity symbol.")
    articles: int | None = Field(
        default=None,
        description="Total number of articles mentioning the symbol.",
    )
    sentiment: float | None = Field(
        default=None,
        description="Average entity sentiment across the analysed articles, "
        "from -1 to +1.",
    )
    sentiment_label: str | None = Field(
        default=None, description="Classification of the average sentiment."
    )
    positive: int = Field(
        default=0, description="Number of positive entity mentions."
    )
    negative: int = Field(
        default=0, description="Number of negative entity mentions."
    )
    neutral: int = Field(
        default=0, description="Number of neutral entity mentions."
    )
    top_headline: str | None = Field(
        default=None, description="Title of the strongest matching article."
    )
    top_headline_date: datetime | None = Field(
        default=None, description="Publication date of the top headline."
    )

    @field_validator("top_headline_date", mode="before", check_fields=False)
    @classmethod
    def date_validate(cls, v):
        """Return the date as a datetime object."""
        return parse_datetime(v) if isinstance(v, str) else v


def _symbol_stats(symbol: str, payload: dict) -> dict:
    """Compute sentiment stats for one symbol from a news payload."""
    articles = payload.get("data", [])
    scores = []
    positive = negative = neutral = 0

    for article in articles:
        for entity in article.get("entities", []):
            if entity.get("symbol") != symbol:
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

    avg = round(sum(scores) / len(scores), 4) if scores else None
    top = articles[0] if articles else {}
    return {
        "symbol": symbol,
        "articles": payload.get("meta", {}).get("found", 0),
        "sentiment": avg,
        "sentiment_label": classify(avg),
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "top_headline": top.get("title"),
        "top_headline_date": top.get("published_at"),
    }


class MarketauxSentimentSummaryFetcher(
    Fetcher[
        MarketauxSentimentSummaryQueryParams,
        list[MarketauxSentimentSummaryData],
    ]
):
    """Transform the query, extract and transform the data from Marketaux."""

    @staticmethod
    def transform_query(
        params: dict[str, Any]
    ) -> MarketauxSentimentSummaryQueryParams:
        """Transform the query parameters."""
        if isinstance(params.get("symbol"), (list, tuple)):
            params["symbol"] = ",".join(str(s) for s in params["symbol"])
        return MarketauxSentimentSummaryQueryParams(**params)

    @staticmethod
    def extract_data(
        query: MarketauxSentimentSummaryQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Extract the data from Marketaux (one request per symbol)."""
        token = get_token(credentials)
        symbols = split_symbols(query.symbol)
        if not symbols:
            raise EmptyDataError("At least one symbol is required.")

        results = []
        for symbol in symbols.split(","):
            params = {
                "symbols": symbol,
                "filter_entities": "true",
                "must_have_entities": "true",
                "sort": "entity_match_score",
                "group_similar": "true",
                "language": query.language,
                "limit": query.limit or 100,
                "published_after": (
                    query.start_date
                    or datetime.now(timezone.utc) - timedelta(days=7)
                ).strftime("%Y-%m-%d"),
            }
            payload = marketaux_get("/news/all", params, token)
            results.append(_symbol_stats(symbol, payload))
        return results

    @staticmethod
    def transform_data(
        query: MarketauxSentimentSummaryQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[MarketauxSentimentSummaryData]:
        """Transform the data into the standard model."""
        if not data:
            raise OpenBBError("No sentiment data could be computed.")
        return [MarketauxSentimentSummaryData(**item) for item in data]
