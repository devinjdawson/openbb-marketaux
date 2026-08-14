"""Marketaux Company News Model."""

# pylint: disable=unused-argument

from datetime import datetime, timedelta, timezone
from typing import Any

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.company_news import (
    CompanyNewsData,
    CompanyNewsQueryParams,
)
from openbb_core.provider.utils.errors import EmptyDataError
from openbb_marketaux.utils.dates import parse_datetime
from openbb_marketaux.utils.helpers import (
    get_token,
    marketaux_get,
    split_symbols,
)
from openbb_marketaux.utils.sentiment import classify
from pydantic import Field, field_validator


class MarketauxCompanyNewsQueryParams(CompanyNewsQueryParams):
    """Marketaux Company News Query.

    Source: https://www.marketaux.com/documentation
    """

    __json_schema_extra__ = {"symbol": {"multiple_items_allowed": True}}

    language: str | None = Field(
        default="en",
        description="Comma separated list of languages to include (e.g. `en,es`).",
    )


def _flatten_entities(article: dict, symbols_requested: str = "") -> dict:
    """Flatten Marketaux article entities into summary numbers."""
    entities = article.get("entities") or []
    if symbols_requested:
        requested = set(symbols_requested.split(","))
        scoped = [e for e in entities if e.get("symbol") in requested] or entities
    else:
        scoped = entities
    scores = [e.get("sentiment_score") for e in scoped]
    scores = [s for s in scores if s is not None]
    matches = [e.get("match_score") for e in scoped]
    matches = [m for m in matches if m is not None]
    return {
        "symbols": ",".join(
            dict.fromkeys(e.get("symbol") for e in entities if e.get("symbol"))
        ),
        "sentiment": round(sum(scores) / len(scores), 4) if scores else None,
        "match_score": round(sum(matches) / len(matches), 4) if matches else None,
    }


def transform_article(article: dict, symbols_requested: str = "") -> dict:
    """Flatten one Marketaux article into model fields."""
    flat = _flatten_entities(article, symbols_requested)
    sentiment = flat["sentiment"]
    return {
        "uuid": article.get("uuid"),
        "date": article.get("published_at"),
        "title": article.get("title"),
        "author": article.get("source"),
        "source": article.get("source"),
        "excerpt": article.get("description") or article.get("snippet"),
        "body": article.get("snippet") or article.get("description"),
        "images": article.get("image_url"),
        "url": article.get("url"),
        "language": article.get("language"),
        "sentiment": sentiment,
        "sentiment_label": classify(sentiment),
        "match_score": flat["match_score"],
        "symbols": flat["symbols"],
    }


class MarketauxCompanyNewsData(CompanyNewsData):
    """Marketaux Company News Data."""

    uuid: str | None = Field(
        default=None, description="The unique identifier of the article."
    )
    source: str | None = Field(
        default=None, description="The domain of the news source."
    )
    language: str | None = Field(
        default=None, description="The language of the article."
    )
    sentiment: float | None = Field(
        default=None,
        description="Average sentiment score of the identified entities "
        "for the requested symbols, from -1 (negative) to +1 (positive).",
    )
    sentiment_label: str | None = Field(
        default=None, description="Classification of the average sentiment."
    )
    match_score: float | None = Field(
        default=None,
        description="Average overall strength of the entity matching.",
    )

    @field_validator("date", mode="before", check_fields=False)
    @classmethod
    def date_validate(cls, v):
        """Return the date as a datetime object."""
        return parse_datetime(v) if isinstance(v, str) else v


class MarketauxCompanyNewsFetcher(
    Fetcher[
        MarketauxCompanyNewsQueryParams,
        list[MarketauxCompanyNewsData],
    ]
):
    """Transform the query, extract and transform the data from Marketaux."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> MarketauxCompanyNewsQueryParams:
        """Transform the query parameters."""
        if isinstance(params.get("symbol"), (list, tuple)):
            params["symbol"] = ",".join(str(s) for s in params["symbol"])
        return MarketauxCompanyNewsQueryParams(**params)

    @staticmethod
    def extract_data(
        query: MarketauxCompanyNewsQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Extract the data from Marketaux."""
        token = get_token(credentials)
        symbols = split_symbols(query.symbol)
        if not symbols:
            raise EmptyDataError("At least one symbol is required.")

        start = query.start_date or (
            datetime.now(timezone.utc) - timedelta(days=7)
        ).date()

        params = {
            "symbols": symbols,
            "filter_entities": "true",
            "must_have_entities": "true",
            "sort": "entity_match_score",
            "group_similar": "true",
            "language": query.language,
            "limit": query.limit or 100,
            "published_after": start.strftime("%Y-%m-%d"),
        }
        if query.end_date:
            params["published_before"] = query.end_date.strftime("%Y-%m-%d")

        payload = marketaux_get("/news/all", params, token)
        return payload.get("data", [])

    @staticmethod
    def transform_data(
        query: MarketauxCompanyNewsQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[MarketauxCompanyNewsData]:
        """Transform the data into the standard model."""
        if not data:
            raise EmptyDataError("No company news found for the query.")
        symbols = split_symbols(query.symbol)
        return [
            MarketauxCompanyNewsData(**transform_article(a, symbols)) for a in data
        ]
