"""Market sentiment widgets built on Marketaux data."""

import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
import plotly.graph_objects as go

import core
from plotly_config import base_layout, get_theme_colors, get_toolbar_config
from services import sentiment as sentiment_service
from services.marketaux import MarketauxError, client

router = APIRouter()


@core.register_widget({
    "name": "Sentiment Summary",
    "description": "Per-symbol news sentiment from Marketaux "
                   "(average entity sentiment over the selected window)",
    "category": "Market Sentiment",
    "type": "table",
    "endpoint": "sentiment_summary",
    "gridData": {"w": 40, "h": 10},
    "source": ["Marketaux"],
    "params": [
        {
            "paramName": "symbols",
            "label": "Symbols",
            "description": "Comma separated list of symbols",
            "type": "text",
            "multiple": True,
            "value": core.DEFAULT_SYMBOLS,
        },
        {
            "paramName": "days",
            "label": "Days",
            "description": "Lookback window in days",
            "type": "number",
            "value": core.SENTIMENT_DAYS,
            "min": 1,
            "max": 90,
        },
    ],
    "data": {
        "table": {
            "showAll": True,
            "columnsDefs": [
                {
                    "field": "symbol",
                    "headerName": "Symbol",
                    "cellDataType": "text",
                    "width": 100,
                    "pinned": "left",
                    "renderFn": "cellOnClick",
                    "renderFnParams": {
                        "actionType": "groupBy",
                        "groupBy": {"paramName": "symbol"},
                    },
                },
                {
                    "field": "classification",
                    "headerName": "Signal",
                    "cellDataType": "text",
                    "width": 110,
                },
                {
                    "field": "total_articles",
                    "headerName": "Articles",
                    "cellDataType": "number",
                    "formatterFn": "int",
                    "width": 100,
                },
                {
                    "field": "avg_sentiment",
                    "headerName": "Avg Sentiment",
                    "cellDataType": "number",
                    "formatterFn": "percent",
                    "renderFn": "greenRed",
                    "width": 130,
                },
                {
                    "field": "positive",
                    "headerName": "Positive",
                    "cellDataType": "number",
                    "formatterFn": "int",
                    "width": 100,
                },
                {
                    "field": "negative",
                    "headerName": "Negative",
                    "cellDataType": "number",
                    "formatterFn": "int",
                    "width": 100,
                },
                {
                    "field": "neutral",
                    "headerName": "Neutral",
                    "cellDataType": "number",
                    "formatterFn": "int",
                    "width": 100,
                },
                {
                    "field": "headline",
                    "headerName": "Top Headline",
                    "cellDataType": "text",
                    "width": 400,
                },
            ],
        }
    },
})
@router.get("/sentiment_summary")
def sentiment_summary(symbols: str = core.DEFAULT_SYMBOLS,
                      days: int = core.SENTIMENT_DAYS):
    """One Marketaux request per symbol: entity sentiment aggregated from articles."""
    symbol_list = core.normalize_symbols(core.split_symbols(symbols))
    if not symbol_list:
        return []

    def fetch():
        with ThreadPoolExecutor(max_workers=min(len(symbol_list), 8)) as pool:
            return list(pool.map(
                lambda symbol: sentiment_service.symbol_article_stats(symbol, days=days),
                symbol_list,
            ))

    try:
        return core.cache.get_or_set(
            f"sentiment_summary:{','.join(symbol_list)}:{days}",
            fetch, core.CACHE_TTL_SENTIMENT,
        )
    except MarketauxError as exc:
        return core.error_response(exc.status_code, exc.code, exc.message)


@core.register_widget({
    "name": "Sentiment Breakdown",
    "description": "Article counts per sentiment bucket with the Bayesian adjusted score "
                   "(Market-Sentiment methodology, 6 Marketaux requests per refresh)",
    "category": "Market Sentiment",
    "type": "chart",
    "endpoint": "sentiment_breakdown",
    "gridData": {"w": 20, "h": 10},
    "source": ["Marketaux"],
    "params": [
        {
            "paramName": "symbols",
            "label": "Symbols",
            "description": "Comma separated list of symbols",
            "type": "text",
            "multiple": True,
            "value": core.DEFAULT_SYMBOLS,
        },
        {
            "paramName": "days",
            "label": "Days",
            "description": "Lookback window in days",
            "type": "number",
            "value": core.SENTIMENT_DAYS,
            "min": 1,
            "max": 90,
        },
    ],
})
@router.get("/sentiment_breakdown")
def sentiment_breakdown(symbols: str = core.DEFAULT_SYMBOLS,
                        days: int = core.SENTIMENT_DAYS):
    """Bar chart of the six sentiment buckets plus the adjusted score."""
    symbol_csv = ",".join(core.normalize_symbols(core.split_symbols(symbols)))

    def fetch():
        return sentiment_service.fetch_bucket_data(symbols=symbol_csv, days=days)

    try:
        data = core.cache.get_or_set(
            f"sentiment_breakdown:{symbol_csv}:{days}",
            fetch, core.CACHE_TTL_SENTIMENT,
        )
    except MarketauxError as exc:
        return core.error_response(exc.status_code, exc.code, exc.message)

    counts = data["counts"]
    labels = [label.replace("_", " ").title() for label in sentiment_service.BUCKET_LABELS]
    values = [counts.get(label, 0) for label in sentiment_service.BUCKET_LABELS]
    colors = [sentiment_service.BUCKET_COLORS[label] for label in sentiment_service.BUCKET_LABELS]
    score = sentiment_service.adjusted_sentiment_score(counts)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=values,
        textposition="outside",
        hovertemplate="%{x}: %{y} articles<extra></extra>",
    ))

    fig.update_layout(
        **base_layout(
            title=f"Adjusted sentiment score: {score:+.3f} "
                  f"({sentiment_service.classify(score)})",
            yaxis_title="Articles",
        ),
    )
    figure_json = json.loads(fig.to_json())
    figure_json["config"] = get_toolbar_config()
    return figure_json


@core.register_widget({
    "name": "Sentiment History",
    "description": "Time series of average entity sentiment per symbol "
                   "(uses Marketaux entity stats, requires Standard plan or above)",
    "category": "Market Sentiment",
    "type": "chart",
    "endpoint": "sentiment_history",
    "gridData": {"w": 20, "h": 10},
    "source": ["Marketaux"],
    "params": [
        {
            "paramName": "symbols",
            "label": "Symbols",
            "description": "Comma separated list of symbols",
            "type": "text",
            "multiple": True,
            "value": core.DEFAULT_SYMBOLS,
        },
        {
            "paramName": "interval",
            "label": "Interval",
            "description": "Time series interval",
            "type": "text",
            "value": "day",
            "options": [
                {"label": "Hour", "value": "hour"},
                {"label": "Day", "value": "day"},
                {"label": "Week", "value": "week"},
                {"label": "Month", "value": "month"},
            ],
        },
        {
            "paramName": "days",
            "label": "Days",
            "description": "Lookback window in days",
            "type": "number",
            "value": core.SENTIMENT_DAYS,
            "min": 1,
            "max": 365,
        },
    ],
})
@router.get("/sentiment_history")
def sentiment_history(symbols: str = core.DEFAULT_SYMBOLS,
                      interval: str = "day", days: int = core.SENTIMENT_DAYS):
    """Sentiment time series from /entity/stats/intraday (paid Marketaux plans)."""
    symbol_csv = ",".join(core.normalize_symbols(core.split_symbols(symbols)))

    def fetch():
        return client.entity_stats_intraday(
            symbols=symbol_csv,
            interval=interval,
            group_by="symbol",
            published_after=sentiment_service.published_after(days),
            date_order="asc",
            limit=50,
        )

    try:
        payload = core.cache.get_or_set(
            f"sentiment_history:{symbol_csv}:{interval}:{days}",
            fetch, core.CACHE_TTL_SENTIMENT,
        )
    except MarketauxError as exc:
        return core.error_response(exc.status_code, exc.code, exc.message)

    series = {}
    for point in payload.get("data", []):
        date = point.get("date")
        for entry in point.get("data", []):
            key = entry.get("key")
            bucket = series.setdefault(key, {"dates": [], "sentiment": [], "documents": []})
            bucket["dates"].append(date)
            bucket["sentiment"].append(entry.get("sentiment_avg"))
            bucket["documents"].append(entry.get("total_documents"))

    colors = get_theme_colors()
    fig = go.Figure()

    for key, bucket in series.items():
        fig.add_trace(go.Scatter(
            x=bucket["dates"],
            y=bucket["sentiment"],
            mode="lines+markers",
            name=key,
            customdata=[[doc] for doc in bucket["documents"]],
            hovertemplate=(
                f"{key}<br>%{{x}}<br>sentiment: %{{y:.3f}}"
                "<br>articles: %{customdata[0]}<extra></extra>"
            ),
            connectgaps=True,
        ))

    fig.add_hline(y=0, line_color=colors["grid"], line_dash="dot")

    fig.update_layout(
        **base_layout(
            title="Average news sentiment over time",
            yaxis_title="Sentiment",
            yaxis=dict(range=[-1, 1], gridcolor=colors["grid"]),
        ),
    )
    figure_json = json.loads(fig.to_json())
    figure_json["config"] = get_toolbar_config()
    return figure_json


@core.register_widget({
    "name": "Trending Entities",
    "description": "Entities trending in the news right now "
                   "(uses Marketaux trending aggregation, requires Standard plan or above)",
    "category": "Market Sentiment",
    "type": "table",
    "endpoint": "trending_entities",
    "gridData": {"w": 20, "h": 10},
    "source": ["Marketaux"],
    "params": [
        {
            "paramName": "countries",
            "label": "Countries",
            "description": "Comma separated exchange countries (e.g. us,ca)",
            "type": "text",
            "value": "us",
        },
        {
            "paramName": "days",
            "label": "Days",
            "description": "Lookback window in days",
            "type": "number",
            "value": 1,
            "min": 1,
            "max": 90,
        },
        {
            "paramName": "limit",
            "label": "Limit",
            "description": "Number of trending entities",
            "type": "number",
            "value": 20,
            "min": 1,
            "max": 100,
        },
    ],
    "data": {
        "table": {
            "showAll": True,
            "columnsDefs": [
                {
                    "field": "key",
                    "headerName": "Symbol",
                    "cellDataType": "text",
                    "width": 100,
                    "pinned": "left",
                    "renderFn": "cellOnClick",
                    "renderFnParams": {
                        "actionType": "groupBy",
                        "groupBy": {"paramName": "symbol"},
                    },
                },
                {
                    "field": "total_documents",
                    "headerName": "Articles",
                    "cellDataType": "number",
                    "formatterFn": "int",
                    "width": 100,
                },
                {
                    "field": "sentiment_avg",
                    "headerName": "Avg Sentiment",
                    "cellDataType": "number",
                    "formatterFn": "percent",
                    "renderFn": "greenRed",
                    "width": 130,
                },
                {
                    "field": "score",
                    "headerName": "Trend Score",
                    "cellDataType": "number",
                    "formatterFn": "none",
                    "width": 130,
                },
            ],
        }
    },
})
@router.get("/trending_entities")
def trending_entities(countries: str = "us", days: int = 1, limit: int = 20):
    """Trending entities from /entity/trending/aggregation (paid Marketaux plans)."""

    def fetch():
        return client.trending_aggregation(
            countries=countries,
            published_after=sentiment_service.published_after(days),
            language="en",
            limit=limit,
        )

    try:
        payload = core.cache.get_or_set(
            f"trending_entities:{countries}:{days}:{limit}",
            fetch, core.CACHE_TTL_SENTIMENT,
        )
    except MarketauxError as exc:
        return core.error_response(exc.status_code, exc.code, exc.message)

    return payload.get("data", [])
