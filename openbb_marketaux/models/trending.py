"""Marketaux Trending Entities Model."""

# pylint: disable=unused-argument

from datetime import date as dateType
from datetime import datetime, timedelta, timezone
from typing import Any

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from openbb_core.provider.utils.descriptions import QUERY_DESCRIPTIONS
from openbb_core.provider.utils.errors import EmptyDataError
from openbb_marketaux.utils.helpers import get_token, marketaux_get
from pydantic import Field, field_validator


class MarketauxTrendingQueryParams(QueryParams):
    """Marketaux Trending Entities Query.

    Source: https://www.marketaux.com/documentation
    """

    start_date: dateType | None = Field(
        default=None,
        description="Start of the window. Defaults to 24 hours ago.",
    )
    countries: str | None = Field(
        default="us",
        description="Comma separated exchange countries (e.g. `us,ca`).",
    )
    language: str | None = Field(
        default="en", description="Comma separated list of languages."
    )
    limit: int | None = Field(
        default=20, description=QUERY_DESCRIPTIONS.get("limit", "")
    )

    @field_validator("start_date", mode="before")
    @classmethod
    def start_date_validate(cls, v) -> dateType:
        """Default to 24 hours ago."""
        if not v:
            v = datetime.now(timezone.utc) - timedelta(days=1)
        return v


class MarketauxTrendingData(Data):
    """Marketaux Trending Entities Data."""

    symbol: str | None = Field(
        default=None, description="The symbol of the trending entity."
    )
    articles: int | None = Field(
        default=None,
        description="Number of news articles the entity was identified in.",
    )
    sentiment: float | None = Field(
        default=None,
        description="Average news sentiment for the entity, from -1 to +1.",
    )
    score: float | None = Field(
        default=None, description="The relevance score for the trending entity."
    )


class MarketauxTrendingFetcher(
    Fetcher[
        MarketauxTrendingQueryParams,
        list[MarketauxTrendingData],
    ]
):
    """Transform the query, extract and transform the data from Marketaux."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> MarketauxTrendingQueryParams:
        """Transform the query parameters."""
        return MarketauxTrendingQueryParams(**params)

    @staticmethod
    def extract_data(
        query: MarketauxTrendingQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Extract the data from Marketaux."""
        token = get_token(credentials)

        params = {
            "countries": query.countries,
            "language": query.language,
            "limit": query.limit or 20,
            "published_after": (
                query.start_date
                or datetime.now(timezone.utc) - timedelta(days=1)
            ).strftime("%Y-%m-%dT%H:%M"),
        }
        payload = marketaux_get("/entity/trending/aggregation", params, token)
        return payload.get("data", [])

    @staticmethod
    def transform_data(
        query: MarketauxTrendingQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[MarketauxTrendingData]:
        """Transform the data into the standard model."""
        if not data:
            raise EmptyDataError("No trending entities found for the query.")
        return [
            MarketauxTrendingData(
                symbol=item.get("key"),
                articles=item.get("total_documents"),
                sentiment=item.get("sentiment_avg"),
                score=item.get("score"),
            )
            for item in data
        ]
