"""Unit-test the Marketaux fetchers with mocked payloads + live error path."""
import warnings

warnings.filterwarnings("ignore")

from openbb_core.provider.utils.errors import UnauthorizedError

from openbb_marketaux.models import (
    company_news as cn,
    equity_search as es,
    sentiment_breakdown as sb,
    sentiment_history as sh,
    sentiment_summary as ss,
    world_news as wn,
)

SAMPLE_ARTICLES = [
    {
        "uuid": "70cb577e-c2dd-4dde-b501-f713823a4939",
        "title": "Trump wins 2024, markets surge globally",
        "description": "Global markets experience a significant surge.",
        "snippet": "Donald Trump has won the 2024 presidential election...",
        "url": "https://example.com/a",
        "image_url": "https://example.com/a.jpg",
        "language": "en",
        "published_at": "2024-11-08T01:24:00.000000Z",
        "source": "killerstartups.com",
        "entities": [
            {
                "symbol": "TSLA",
                "name": "Tesla, Inc.",
                "match_score": 12.133104,
                "sentiment_score": 0.7783,
            }
        ],
    },
    {
        "uuid": "ed35bdcd-6f6a-4007-9949-b769fbe2e36d",
        "title": "Amazon.com mulls Anthropic investment",
        "description": "Amazon in talks for new investment.",
        "snippet": "(Reuters) - Amazon is in talks...",
        "url": "https://example.com/b",
        "image_url": "https://example.com/b.jpg",
        "language": "en",
        "published_at": "2024-11-07T23:49:09.000000Z",
        "source": "investing.com",
        "entities": [
            {"symbol": "AMZN", "match_score": 34.292408, "sentiment_score": 0},
            {"symbol": "TSLA", "match_score": 10.0, "sentiment_score": -0.2},
        ],
    },
]

calls = []

BUCKET_COUNTS = {
    (0.15, 0.39): 10,
    (0.4, 0.69): 5,
    (0.7, 1.0): 2,
    (-0.39, -0.15): 4,
    (-0.69, -0.4): 3,
    (-1.0, -0.7): 1,
}


def fake_get(path, params, token, timeout=30):
    calls.append((path, dict(params), token))
    if path == "/news/all":
        if "sentiment_gte" in params and "sentiment_lte" in params:
            key = (params["sentiment_gte"], params["sentiment_lte"])
            return {"meta": {"found": BUCKET_COUNTS[key]}, "data": []}
        return {"meta": {"found": 140037}, "data": SAMPLE_ARTICLES}
    if path == "/entity/search":
        return {
            "data": [
                {
                    "symbol": "TSLA",
                    "name": "Tesla, Inc.",
                    "type": "equity",
                    "industry": "Consumer Cyclical",
                    "exchange": None,
                    "exchange_long": None,
                    "country": "us",
                }
            ]
        }
    if path == "/entity/trending/aggregation":
        return {
            "data": [
                {
                    "key": "NVDA",
                    "total_documents": 22,
                    "sentiment_avg": 0.4360,
                    "score": 3.79,
                }
            ]
        }
    if path == "/entity/stats/intraday":
        return {
            "data": [
                {
                    "date": "2024-11-10T00:00:00.000Z",
                    "data": [
                        {"key": "TSLA", "total_documents": 14, "sentiment_avg": 0.388},
                        {"key": "MSFT", "total_documents": 10, "sentiment_avg": 0.39},
                    ],
                }
            ]
        }
    raise AssertionError(f"unexpected path {path}")


# Patch the per-module references
for mod in (cn, wn, es, sb, ss, sh):
    mod.marketaux_get = fake_get

CREDS = {"marketaux_api_key": "test-token"}

# --- CompanyNews ---
q = cn.MarketauxCompanyNewsFetcher.transform_query({"symbol": ["tsla", "amzn"], "limit": 5})
assert q.symbol == "TSLA,AMZN"
data = cn.MarketauxCompanyNewsFetcher.extract_data(q, CREDS)
result = cn.MarketauxCompanyNewsFetcher.transform_data(q, data)
assert len(result) == 2
assert result[0].title.startswith("Trump wins")
assert result[0].sentiment == 0.7783
assert result[0].sentiment_label == "Bullish"
assert result[0].date.isoformat().startswith("2024-11-08T01:24")
assert result[0].symbols == "TSLA"
assert result[1].symbols == "AMZN,TSLA"
assert abs(result[1].sentiment - (-0.1)) < 1e-6
first_call = calls[0]
assert first_call[2] == "test-token"
assert first_call[1]["symbols"] == "TSLA,AMZN"
assert first_call[1]["filter_entities"] == "true"
print("CompanyNews pipeline OK")

# --- WorldNews ---
q = wn.MarketauxWorldNewsFetcher.transform_query({"sentiment": "positive", "limit": 10, "search": "ipo"})
data = wn.MarketauxWorldNewsFetcher.extract_data(q, CREDS)
result = wn.MarketauxWorldNewsFetcher.transform_data(q, data)
assert len(result) == 2 and result[0].author == "killerstartups.com"
assert calls[-1][1]["sentiment_gte"] == 0.15 and calls[-1][1]["search"] == "ipo"
print("WorldNews pipeline OK")

# --- EquitySearch ---
q = es.MarketauxEquitySearchFetcher.transform_query({"query": "tesla", "countries": "us"})
data = es.MarketauxEquitySearchFetcher.extract_data(q, CREDS)
result = es.MarketauxEquitySearchFetcher.transform_data(q, data)
assert result[0].symbol == "TSLA" and result[0].industry == "Consumer Cyclical"
assert calls[-1][1]["search"] == "tesla"
q2 = es.MarketauxEquitySearchFetcher.transform_query({"query": "TSLA", "is_symbol": True})
es.MarketauxEquitySearchFetcher.extract_data(q2, CREDS)
assert calls[-1][1]["symbols"] == "TSLA" and "search" not in calls[-1][1]
print("EquitySearch pipeline OK")

# --- SentimentBreakdown ---
q = sb.MarketauxSentimentBreakdownFetcher.transform_query({"symbol": "TSLA"})
counts = sb.MarketauxSentimentBreakdownFetcher.extract_data(q, CREDS)
assert len([c for c in calls[-6:] if c[0] == "/news/all"]) == 6
result = sb.MarketauxSentimentBreakdownFetcher.transform_data(q, counts)
assert result.total_articles == 25
raw = (10 * 1 + 5 * 2 + 2 * 3) - (4 * 1 + 3 * 2 + 1 * 3)
weighted = (10 + 4) * 1 + (5 + 3) * 2 + (2 + 1) * 3
assert abs(result.adjusted_score - round(raw / (weighted + 100), 4)) < 1e-6
assert result.sentiment_label == "Neutral"
print("SentimentBreakdown pipeline OK:", result.adjusted_score, result.sentiment_label)

# --- SentimentSummary ---
q = ss.MarketauxSentimentSummaryFetcher.transform_query({"symbol": "TSLA,AMZN"})
data = ss.MarketauxSentimentSummaryFetcher.extract_data(q, CREDS)
assert len(data) == 2
result = ss.MarketauxSentimentSummaryFetcher.transform_data(q, data)
tsla = next(r for r in result if r.symbol == "TSLA")
assert tsla.articles == 140037
assert tsla.sentiment == round((0.7783 + -0.2) / 2, 4)
assert tsla.positive == 1 and tsla.negative == 1 and tsla.neutral == 0
amzn = next(r for r in result if r.symbol == "AMZN")
assert amzn.sentiment == 0.0 and amzn.neutral == 1
assert tsla.top_headline == "Trump wins 2024, markets surge globally"
assert tsla.top_headline_date.isoformat().startswith("2024-11-08")
print("SentimentSummary pipeline OK")

# --- SentimentHistory ---
q = sh.MarketauxSentimentHistoryFetcher.transform_query({"symbol": "TSLA,MSFT", "interval": "day"})
data = sh.MarketauxSentimentHistoryFetcher.extract_data(q, CREDS)
result = sh.MarketauxSentimentHistoryFetcher.transform_data(q, data)
assert len(result) == 2
assert result[0].symbol == "TSLA" and result[0].articles == 14
assert result[0].date.isoformat().startswith("2024-11-10")
assert calls[-1][1]["interval"] == "day" and calls[-1][1]["date_order"] == "asc"
print("SentimentHistory pipeline OK")

# --- Trending ---
from openbb_marketaux.models import trending as tr

tr.marketaux_get = fake_get
q = tr.MarketauxTrendingFetcher.transform_query({"countries": "us"})
data = tr.MarketauxTrendingFetcher.extract_data(q, CREDS)
result = tr.MarketauxTrendingFetcher.transform_data(q, data)
assert result[0].symbol == "NVDA" and result[0].articles == 22
print("Trending pipeline OK")

# --- Missing credentials ---
try:
    cn.MarketauxCompanyNewsFetcher.extract_data(
        cn.MarketauxCompanyNewsFetcher.transform_query({"symbol": "AAPL"}), None
    )
    raise AssertionError("should have raised UnauthorizedError")
except UnauthorizedError as exc:
    assert "marketaux_api_key" in str(exc)
print("Missing-credential error OK")

print("\nALL FETCHER PIPELINE TESTS PASSED")
