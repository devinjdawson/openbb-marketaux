# pylint: disable=import-outside-toplevel, W0613:unused-argument
"""Marketaux Router."""

from openbb_core.app.model.command_context import CommandContext
from openbb_core.app.model.example import APIEx
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.provider_interface import (
    ExtraParams,
    ProviderChoices,
    StandardParams,
)
from openbb_core.app.query import Query
from openbb_core.app.router import Router

router = Router(prefix="", description="Marketaux news sentiment and analytics.")


@router.command(
    model="TrendingEntities",
    examples=[
        APIEx(parameters={"provider": "marketaux"}),
        APIEx(
            description="Trending entities in Canada over the last 48 hours.",
            parameters={
                "countries": "ca",
                "start_date": "2026-08-12",
                "provider": "marketaux",
            },
        ),
    ],
)
async def trending(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Trending Entities. Identify entities currently trending in the news."""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="SentimentSummary",
    examples=[
        APIEx(parameters={"symbol": "AAPL,TSLA", "provider": "marketaux"}),
        APIEx(
            description="Sentiment summary over the last 30 days.",
            parameters={
                "symbol": "AAPL,TSLA,NVDA",
                "start_date": "2026-07-15",
                "provider": "marketaux",
            },
        ),
    ],
)
async def sentiment(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Sentiment Summary. Per-symbol news sentiment aggregated from articles."""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="SentimentBreakdown",
    examples=[
        APIEx(parameters={"symbol": "TSLA", "provider": "marketaux"}),
        APIEx(
            description="Market-wide sentiment breakdown over the last 24 hours.",
            parameters={"start_date": "2026-08-13", "provider": "marketaux"},
        ),
    ],
)
async def sentiment_breakdown(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Sentiment Breakdown. Article counts per sentiment bucket with a
    Bayesian-adjusted score."""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="SentimentHistory",
    examples=[
        APIEx(parameters={"symbol": "AAPL,TSLA", "provider": "marketaux"}),
        APIEx(
            description="Weekly sentiment history over the last 3 months.",
            parameters={
                "symbol": "AAPL,TSLA",
                "interval": "week",
                "start_date": "2026-05-14",
                "provider": "marketaux",
            },
        ),
    ],
)
async def sentiment_history(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Sentiment History. Time series of average entity sentiment.
    Requires a Marketaux Standard plan or above."""
    return await OBBject.from_query(Query(**locals()))
