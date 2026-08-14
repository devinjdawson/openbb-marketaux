"""Marketaux World News Model."""

# pylint: disable=unused-argument

from datetime import datetime, timedelta, timezone
from typing import Any

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.world_news import (
    WorldNewsData,
    WorldNewsQueryParams,
)
from openbb_core.provider.utils.errors import EmptyDataError
from openbb_marketaux.models.company_news import transform_article
from openbb_marketaux.utils.dates import parse_datetime
from openbb_marketaux.utils.helpers import get_token, marketaux_get
from openbb_marketaux.utils.sentiment import classify
from pydantic import Field, field_validator


class MarketauxWorldNewsQueryParams(WorldNewsQueryParams):
    """Marketaux World News Query.

    Source: https://www.marketaux.com/documentation
    """

    search: str | None = Field(
        default=None,
        description="Free-text search over article titles and bodies. "
        "Supports advanced queries: `+` AND, `|` OR, `-` NOT, `\"` phrase, "
        "`*` prefix, `(` `)` precedence.",
    )
    countries: str | None = Field(
        default=None,
        description="Comma separated exchange countries of entities to "
        "include (e.g. `us,ca`).",
    )
    language: str | None = Field(
        default="en",
        description="Comma separated list of languages to include (e.g. `en,es`).",
    )
    sentiment: str | None = Field(
        default=None,
        description="Filter by entity sentiment: `positive`, `negative` or `neutral`.",
    )


class MarketauxWorldNewsData(WorldNewsData):
    """Marketaux World News Data."""

    uuid: str | None = Field(
        default=None, description="The unique identifier of the article."
    )
    source: str | None = Field(
        default=None, description="The domain of the news source."
    )
    language: str | None = Field(
        default=None, description="The language of the article."
    )
    symbols: str | None = Field(
        default=None, description="Symbols of entities identified in the article."
    )
    sentiment: float | None = Field(
        default=None,
        description="Average sentiment score of the identified entities, "
        "from -1 (negative) to +1 (positive).",
    )
    sentiment_label: str | None = Field(
        default=None, description="Classification of the average sentiment."
    )

    @field_validator("date", mode="before", check_fields=False)
    @classmethod
    def date_validate(cls, v):
        """Return the date as a datetime object."""
        return parse_datetime(v) if isinstance(v, str) else v


class MarketauxWorldNewsFetcher(
    Fetcher[
        MarketauxWorldNewsQueryParams,
        list[MarketauxWorldNewsData],
    ]
):
    """Transform the query, extract and transform the data from Marketaux."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> MarketauxWorldNewsQueryParams:
        """Transform the query parameters."""
        return MarketauxWorldNewsQueryParams(**params)

    @staticmethod
    def extract_data(
        query: MarketauxWorldNewsQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Extract the data from Marketaux."""
        token = get_token(credentials)

        start = query.start_date or (
            datetime.now(timezone.utc) - timedelta(days=14)
        ).date()

        params = {
            "search": query.search,
            "countries": query.countries,
            "language": query.language,
            "limit": query.limit or 100,
            "group_similar": "true",
            "published_after": start.strftime("%Y-%m-%d"),
        }
        if query.end_date:
            params["published_before"] = query.end_date.strftime("%Y-%m-%d")
        if query.sentiment == "positive":
            params["sentiment_gte"] = 0.15
        elif query.sentiment == "negative":
            params["sentiment_lte"] = -0.15
        elif query.sentiment == "neutral":
            params["sentiment_gte"] = -0.15
            params["sentiment_lte"] = 0.15

        payload = marketaux_get("/news/all", params, token)
        return payload.get("data", [])

    @staticmethod
    def transform_data(
        query: MarketauxWorldNewsQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[MarketauxWorldNewsData]:
        """Transform the data into the standard model."""
        if not data:
            raise EmptyDataError("No world news found for the query.")
        return [MarketauxWorldNewsData(**transform_article(a)) for a in data]
