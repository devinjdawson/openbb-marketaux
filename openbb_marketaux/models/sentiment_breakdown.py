"""Marketaux Sentiment Breakdown Model (Market-Sentiment methodology)."""

# pylint: disable=unused-argument

from datetime import date as dateType
from datetime import datetime, timedelta, timezone
from typing import Any

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from openbb_core.provider.utils.errors import EmptyDataError
from openbb_marketaux.utils.helpers import (
    get_token,
    marketaux_get,
    split_symbols,
)
from openbb_marketaux.utils.sentiment import (
    adjusted_sentiment_score,
    bucket_requests,
    classify,
)
from pydantic import Field, field_validator


class MarketauxSentimentBreakdownQueryParams(QueryParams):
    """Marketaux Sentiment Breakdown Query.

    Counts articles per sentiment bucket (weak/moderate/strong x
    positive/negative) and computes a Bayesian-adjusted score, following
    the Market-Sentiment methodology. Costs six Marketaux API requests
    per call (one per bucket).
    """

    symbol: str | None = Field(
        default=None,
        description="Comma separated list of symbols. When empty, the "
        "breakdown covers all financial news.",
    )
    start_date: dateType | None = Field(
        default=None,
        description="Start of the lookback window. Defaults to 7 days ago.",
    )
    language: str | None = Field(
        default="en", description="Comma separated list of languages."
    )

    @field_validator("start_date", mode="before")
    @classmethod
    def start_date_validate(cls, v) -> dateType:
        """Default to 7 days ago."""
        if not v:
            v = datetime.now(timezone.utc) - timedelta(days=7)
        return v


class MarketauxSentimentBreakdownData(Data):
    """Marketaux Sentiment Breakdown Data."""

    weak_positive: int = Field(
        default=0, description="Articles with sentiment in [0.15, 0.39]."
    )
    moderate_positive: int = Field(
        default=0, description="Articles with sentiment in [0.4, 0.69]."
    )
    strong_positive: int = Field(
        default=0, description="Articles with sentiment in [0.7, 1.0]."
    )
    weak_negative: int = Field(
        default=0, description="Articles with sentiment in [-0.39, -0.15]."
    )
    moderate_negative: int = Field(
        default=0, description="Articles with sentiment in [-0.69, -0.4]."
    )
    strong_negative: int = Field(
        default=0, description="Articles with sentiment in [-1.0, -0.7]."
    )
    total_articles: int = Field(
        default=0, description="Total articles counted across the buckets."
    )
    adjusted_score: float = Field(
        description="Bayesian-adjusted sentiment score in [-1, 1]."
    )
    sentiment_label: str = Field(
        description="Classification of the adjusted score."
    )


class MarketauxSentimentBreakdownFetcher(
    Fetcher[
        MarketauxSentimentBreakdownQueryParams,
        MarketauxSentimentBreakdownData,
    ]
):
    """Transform the query, extract and transform the data from Marketaux."""

    @staticmethod
    def transform_query(
        params: dict[str, Any]
    ) -> MarketauxSentimentBreakdownQueryParams:
        """Transform the query parameters."""
        if isinstance(params.get("symbol"), (list, tuple)):
            params["symbol"] = ",".join(str(s) for s in params["symbol"])
        return MarketauxSentimentBreakdownQueryParams(**params)

    @staticmethod
    def extract_data(
        query: MarketauxSentimentBreakdownQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> dict:
        """Extract the bucket counts from Marketaux (six requests)."""
        token = get_token(credentials)
        symbols = split_symbols(query.symbol)

        counts = {}
        for label, gte, lte in bucket_requests():
            params = {
                "sentiment_gte": gte,
                "sentiment_lte": lte,
                "language": query.language,
                "limit": 1,
                "published_after": (
                    query.start_date
                    or datetime.now(timezone.utc) - timedelta(days=7)
                ).strftime("%Y-%m-%d"),
            }
            if symbols:
                params["symbols"] = symbols
                params["filter_entities"] = "true"
                params["must_have_entities"] = "true"
            payload = marketaux_get("/news/all", params, token)
            counts[label] = payload.get("meta", {}).get("found", 0)
        return counts

    @staticmethod
    def transform_data(
        query: MarketauxSentimentBreakdownQueryParams,
        data: dict,
        **kwargs: Any,
    ) -> MarketauxSentimentBreakdownData:
        """Transform the bucket counts into the adjusted score."""
        if not data:
            raise EmptyDataError("No articles found for the query.")
        score = round(adjusted_sentiment_score(data), 4)
        return MarketauxSentimentBreakdownData(
            weak_positive=data.get("weak_positive", 0),
            moderate_positive=data.get("moderate_positive", 0),
            strong_positive=data.get("strong_positive", 0),
            weak_negative=data.get("weak_negative", 0),
            moderate_negative=data.get("moderate_negative", 0),
            strong_negative=data.get("strong_negative", 0),
            total_articles=sum(data.values()),
            adjusted_score=score,
            sentiment_label=classify(score),
        )
