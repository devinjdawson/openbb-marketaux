"""Marketaux provider module."""

from openbb_core.provider.abstract.provider import Provider
from openbb_marketaux.models.company_news import MarketauxCompanyNewsFetcher
from openbb_marketaux.models.equity_search import MarketauxEquitySearchFetcher
from openbb_marketaux.models.sentiment_breakdown import (
    MarketauxSentimentBreakdownFetcher,
)
from openbb_marketaux.models.sentiment_history import MarketauxSentimentHistoryFetcher
from openbb_marketaux.models.sentiment_summary import MarketauxSentimentSummaryFetcher
from openbb_marketaux.models.trending import MarketauxTrendingFetcher
from openbb_marketaux.models.world_news import MarketauxWorldNewsFetcher

marketaux_provider = Provider(
    name="marketaux",
    website="https://www.marketaux.com",
    description="""Marketaux is a global financial news and entity analytics
platform. It tracks 5,000+ news sources in 30+ languages and identifies
200,000+ entities across 80+ markets, providing news feeds with entity-level
sentiment scores, trending entity analytics, and entity metadata.""",
    credentials=["api_key"],
    fetcher_dict={
        "CompanyNews": MarketauxCompanyNewsFetcher,
        "WorldNews": MarketauxWorldNewsFetcher,
        "EquitySearch": MarketauxEquitySearchFetcher,
        "TrendingEntities": MarketauxTrendingFetcher,
        "SentimentSummary": MarketauxSentimentSummaryFetcher,
        "SentimentBreakdown": MarketauxSentimentBreakdownFetcher,
        "SentimentHistory": MarketauxSentimentHistoryFetcher,
    },
    repr_name="Marketaux",
    instructions="Sign up for a free API token at "
    "https://www.marketaux.com/register, then set it with "
    "`obb.user.credentials.marketaux_api_key = '***'` and "
    "`obb.account.save()`.",
)
