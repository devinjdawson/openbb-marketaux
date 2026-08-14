"""Marketaux Equity Search Model."""

# pylint: disable=unused-argument

from typing import Any

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_search import (
    EquitySearchData,
    EquitySearchQueryParams,
)
from openbb_core.provider.utils.errors import EmptyDataError
from openbb_marketaux.utils.helpers import get_token, marketaux_get
from pydantic import Field


class MarketauxEquitySearchQueryParams(EquitySearchQueryParams):
    """Marketaux Equity Search Query.

    Source: https://www.marketaux.com/documentation
    """

    countries: str | None = Field(
        default=None,
        description="Comma separated ISO 3166-1 country codes of the exchange "
        "(e.g. `us,ca`).",
    )
    types: str | None = Field(
        default=None,
        description="Comma separated entity types to include "
        "(e.g. `equity,etf,index,cryptocurrency`).",
    )
    industries: str | None = Field(
        default=None,
        description="Comma separated industries to include "
        "(e.g. `Technology,Energy`).",
    )
    exchanges: str | None = Field(
        default=None, description="Comma separated exchange identifiers."
    )


class MarketauxEquitySearchData(EquitySearchData):
    """Marketaux Equity Search Data."""

    type: str | None = Field(default=None, description="The entity type.")
    industry: str | None = Field(
        default=None, description="The entity industry."
    )
    exchange: str | None = Field(
        default=None, description="The exchange identifier."
    )
    exchange_long: str | None = Field(
        default=None, description="The exchange name."
    )
    country: str | None = Field(
        default=None,
        description="The ISO 3166-1 country code of the exchange locale.",
    )


class MarketauxEquitySearchFetcher(
    Fetcher[
        MarketauxEquitySearchQueryParams,
        list[MarketauxEquitySearchData],
    ]
):
    """Transform the query, extract and transform the data from Marketaux."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> MarketauxEquitySearchQueryParams:
        """Transform the query parameters."""
        return MarketauxEquitySearchQueryParams(**params)

    @staticmethod
    def extract_data(
        query: MarketauxEquitySearchQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Extract the data from Marketaux."""
        token = get_token(credentials)

        params = {
            "countries": query.countries,
            "types": query.types,
            "industries": query.industries,
            "exchanges": query.exchanges,
        }
        if query.is_symbol:
            params["symbols"] = query.query.upper()
        else:
            params["search"] = query.query

        payload = marketaux_get("/entity/search", params, token)
        return payload.get("data", [])

    @staticmethod
    def transform_data(
        query: MarketauxEquitySearchQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[MarketauxEquitySearchData]:
        """Transform the data into the standard model."""
        if not data:
            raise EmptyDataError("No entities found for the query.")
        return [
            MarketauxEquitySearchData(
                symbol=item.get("symbol"),
                name=item.get("name"),
                type=item.get("type"),
                industry=item.get("industry"),
                exchange=item.get("exchange"),
                exchange_long=item.get("exchange_long"),
                country=item.get("country"),
            )
            for item in data
        ]
