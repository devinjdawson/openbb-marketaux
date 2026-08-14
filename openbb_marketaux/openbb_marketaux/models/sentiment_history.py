"""Marketaux Sentiment History Model (entity stats time series)."""

# pylint: disable=unused-argument

from datetime import date as dateType
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

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
from pydantic import Field, field_validator


class MarketauxSentimentHistoryQueryParams(QueryParams):
    """Marketaux Sentiment History Query.

    Uses the Marketaux entity stats intraday endpoint, which requires a
    Standard plan or above.

    Source: https://www.marketaux.com/documentation
    """

    symbol: str | None = Field(
        default=None,
        description="Comma separated list of symbols. When empty, the best "
        "performing entities are returned.",
    )
    interval: Literal["minute", "hour", "day", "week", "month", "quarter", "year"] = (
        Field(
            default="day",
            description="Interval of the time series. Marketaux applies a "
            "maximum window per interval (minute=7d, hour=1m, day=3y, "
            "week=5y, month=5y, quarter=10y, year=10y).",
        )
    )
    start_date: dateType | None = Field(
        default=None,
        description="Start of the lookback window. Defaults to 7 days ago.",
    )
    language: str | None = Field(
        default="en", description="Comma separated list of languages."
    )
    limit: int | None = Field(
        default=50, description="Maximum number of entities to return."
    )

    @field_validator("start_date", mode="before")
    @classmethod
    def start_date_validate(cls, v) -> dateType:
        """Default to 7 days ago."""
        if not v:
            v = datetime.now(timezone.utc) - timedelta(days=7)
        return v


class MarketauxSentimentHistoryData(Data):
    """Marketaux Sentiment History Data."""

    date: datetime = Field(description="Date of the time series data point.")
    symbol: str | None = Field(
        default=None, description="The entity symbol (the group key)."
    )
    articles: int | None = Field(
        default=None,
        description="Number of documents the entity was identified in.",
    )
    sentiment: float | None = Field(
        default=None, description="Average sentiment for the interval."
    )

    @field_validator("date", mode="before", check_fields=False)
    @classmethod
    def date_validate(cls, v):
        """Return the date as a datetime object."""
        return parse_datetime(v) if isinstance(v, str) else v


class MarketauxSentimentHistoryFetcher(
    Fetcher[
        MarketauxSentimentHistoryQueryParams,
        list[MarketauxSentimentHistoryData],
    ]
):
    """Transform the query, extract and transform the data from Marketaux."""

    @staticmethod
    def transform_query(
        params: dict[str, Any]
    ) -> MarketauxSentimentHistoryQueryParams:
        """Transform the query parameters."""
        if isinstance(params.get("symbol"), (list, tuple)):
            params["symbol"] = ",".join(str(s) for s in params["symbol"])
        return MarketauxSentimentHistoryQueryParams(**params)

    @staticmethod
    def extract_data(
        query: MarketauxSentimentHistoryQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Extract the data from Marketaux."""
        token = get_token(credentials)
        symbols = split_symbols(query.symbol)

        params = {
            "symbols": symbols or None,
            "interval": query.interval,
            "group_by": "symbol",
            "language": query.language,
            "limit": query.limit or 50,
            "date_order": "asc",
            "published_after": (
                query.start_date
                or datetime.now(timezone.utc) - timedelta(days=7)
            ).strftime("%Y-%m-%dT%H:%M"),
        }
        payload = marketaux_get("/entity/stats/intraday", params, token)
        return payload.get("data", [])

    @staticmethod
    def transform_data(
        query: MarketauxSentimentHistoryQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[MarketauxSentimentHistoryData]:
        """Flatten the nested time series into rows."""
        rows = []
        for point in data:
            for entry in point.get("data", []):
                rows.append(
                    MarketauxSentimentHistoryData(
                        date=point.get("date"),
                        symbol=entry.get("key"),
                        articles=entry.get("total_documents"),
                        sentiment=entry.get("sentiment_avg"),
                    )
                )
        if not rows:
            raise EmptyDataError("No sentiment history found for the query.")
        return rows
