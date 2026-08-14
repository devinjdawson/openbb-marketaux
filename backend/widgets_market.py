"""Yahoo Finance market data widgets and Marketaux entity search."""

import json

from fastapi import APIRouter
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import core
from plotly_config import base_layout, get_theme_colors, get_toolbar_config
from services import yahoo
from services.marketaux import MarketauxError, client

router = APIRouter()

WATCHLIST_OPTIONS = [
    {"label": "Apple Inc.", "value": "AAPL"},
    {"label": "Microsoft Corporation", "value": "MSFT"},
    {"label": "Amazon.com Inc.", "value": "AMZN"},
    {"label": "Alphabet Inc.", "value": "GOOGL"},
    {"label": "Tesla Inc.", "value": "TSLA"},
    {"label": "NVIDIA Corporation", "value": "NVDA"},
    {"label": "Meta Platforms Inc.", "value": "META"},
    {"label": "Berkshire Hathaway Inc.", "value": "BRK-B"},
    {"label": "JPMorgan Chase & Co.", "value": "JPM"},
    {"label": "Johnson & Johnson", "value": "JNJ"},
    {"label": "Visa Inc.", "value": "V"},
    {"label": "Exxon Mobil Corporation", "value": "XOM"},
    {"label": "Advanced Micro Devices Inc.", "value": "AMD"},
    {"label": "Netflix Inc.", "value": "NFLX"},
    {"label": "The Walt Disney Company", "value": "DIS"},
    {"label": "SPDR S&P 500 ETF Trust", "value": "SPY"},
    {"label": "Invesco QQQ Trust", "value": "QQQ"},
    {"label": "Bitcoin USD", "value": "BTC-USD"},
    {"label": "Ethereum USD", "value": "ETH-USD"},
    {"label": "Gold Futures", "value": "GC=F"},
]


@router.get("/symbol_options")
def symbol_options():
    """Static symbol dropdown options (no API cost)."""
    return WATCHLIST_OPTIONS


@core.register_widget({
    "name": "Quotes",
    "description": "Live quotes from Yahoo Finance (free, no API key). "
                   "Click a symbol to update widgets in Group 1.",
    "category": "Market Data",
    "type": "table",
    "endpoint": "yahoo_quotes",
    "gridData": {"w": 20, "h": 10},
    "source": ["Yahoo Finance"],
    "params": [
        {
            "paramName": "symbols",
            "label": "Symbols",
            "description": "Comma separated list of Yahoo Finance symbols",
            "type": "text",
            "multiple": True,
            "value": core.DEFAULT_SYMBOLS,
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
                    "field": "name",
                    "headerName": "Name",
                    "cellDataType": "text",
                    "width": 180,
                },
                {
                    "field": "price",
                    "headerName": "Price",
                    "cellDataType": "number",
                    "formatterFn": "none",
                    "width": 100,
                },
                {
                    "field": "change",
                    "headerName": "Change",
                    "cellDataType": "number",
                    "formatterFn": "none",
                    "renderFn": "greenRed",
                    "width": 100,
                },
                {
                    "field": "change_pct",
                    "headerName": "Change %",
                    "cellDataType": "number",
                    "formatterFn": "percent",
                    "renderFn": "greenRed",
                    "width": 110,
                },
                {
                    "field": "volume",
                    "headerName": "Volume",
                    "cellDataType": "number",
                    "formatterFn": "int",
                    "width": 120,
                },
                {
                    "field": "market_cap",
                    "headerName": "Market Cap",
                    "cellDataType": "number",
                    "formatterFn": "int",
                    "width": 130,
                },
                {
                    "field": "week52_high",
                    "headerName": "52W High",
                    "cellDataType": "number",
                    "formatterFn": "none",
                    "width": 100,
                },
                {
                    "field": "week52_low",
                    "headerName": "52W Low",
                    "cellDataType": "number",
                    "formatterFn": "none",
                    "width": 100,
                },
                {
                    "field": "currency",
                    "headerName": "Currency",
                    "cellDataType": "text",
                    "width": 90,
                },
            ],
        }
    },
})
@router.get("/yahoo_quotes")
def yahoo_quotes(symbols: str = core.DEFAULT_SYMBOLS):
    """Live quote summaries from Yahoo Finance."""
    symbol_list = core.split_symbols(symbols)
    if not symbol_list:
        return []
    try:
        return yahoo.get_quotes(symbol_list)
    except Exception as exc:
        return core.error_response(502, "yahoo_request_failed", str(exc))


@core.register_widget({
    "name": "Price Chart",
    "description": "Price history from Yahoo Finance, linked to Group 1",
    "category": "Market Data",
    "type": "chart",
    "endpoint": "yahoo_price_chart",
    "gridData": {"w": 24, "h": 12},
    "source": ["Yahoo Finance"],
    "params": [
        [
            {
                "paramName": "symbol",
                "label": "Symbol",
                "description": "Yahoo Finance symbol",
                "type": "endpoint",
                "optionsEndpoint": "/symbol_options",
                "value": "AAPL",
            },
            {
                "paramName": "period",
                "label": "Period",
                "description": "History period",
                "type": "text",
                "value": "3mo",
                "options": [
                    {"label": "1 Week", "value": "5d"},
                    {"label": "1 Month", "value": "1mo"},
                    {"label": "3 Months", "value": "3mo"},
                    {"label": "6 Months", "value": "6mo"},
                    {"label": "1 Year", "value": "1y"},
                    {"label": "2 Years", "value": "2y"},
                    {"label": "5 Years", "value": "5y"},
                ],
            },
        ],
        [
            {
                "paramName": "chart_type",
                "label": "Chart Type",
                "description": "Line or candlestick",
                "type": "text",
                "value": "line",
                "options": [
                    {"label": "Line", "value": "line"},
                    {"label": "Candlestick", "value": "candlestick"},
                ],
            },
        ],
    ],
})
@router.get("/yahoo_price_chart")
def yahoo_price_chart(symbol: str = "AAPL", period: str = "3mo",
                      chart_type: str = "line"):
    """OHLCV price chart from Yahoo Finance."""
    symbol = symbol.upper()
    interval = "1h" if period in ("5d",) else "1d"
    try:
        bars = yahoo.get_history(symbol, period=period, interval=interval)
    except Exception as exc:
        return core.error_response(502, "yahoo_request_failed", str(exc))

    if not bars:
        return core.error_response(
            404, "no_data", f"No price history found for {symbol}."
        )

    colors = get_theme_colors()
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25], vertical_spacing=0.03,
    )

    dates = [bar["date"] for bar in bars]
    closes = [bar["close"] for bar in bars]
    volumes = [bar["volume"] for bar in bars]

    if chart_type == "candlestick":
        fig.add_trace(go.Candlestick(
            x=dates,
            open=[bar["open"] for bar in bars],
            high=[bar["high"] for bar in bars],
            low=[bar["low"] for bar in bars],
            close=closes,
            name=symbol,
            increasing_line_color=colors["positive"],
            decreasing_line_color=colors["negative"],
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=dates,
            y=closes,
            mode="lines",
            name=symbol,
            line=dict(width=2, color=colors["main_line"]),
        ), row=1, col=1)

    volume_colors = [
        colors["positive"]
        if (bar["close"] or 0) >= (bar["open"] or 0)
        else colors["negative"]
        for bar in bars
    ]
    fig.add_trace(go.Bar(
        x=dates, y=volumes, name="Volume",
        marker_color=volume_colors, opacity=0.6, showlegend=False,
    ), row=2, col=1)

    fig.update_layout(
        **base_layout(title=f"{symbol} — {period}"),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    figure_json = json.loads(fig.to_json())
    figure_json["config"] = get_toolbar_config()
    return figure_json


@core.register_widget({
    "name": "Entity Search",
    "description": "Search the entities tracked by Marketaux",
    "category": "Market Data",
    "type": "table",
    "endpoint": "entity_search",
    "gridData": {"w": 16, "h": 12},
    "source": ["Marketaux"],
    "params": [
        {
            "paramName": "search",
            "label": "Search",
            "description": "Entity name or symbol",
            "type": "text",
            "value": "tesla",
        },
        {
            "paramName": "countries",
            "label": "Countries",
            "description": "Comma separated exchange countries",
            "type": "text",
            "value": "us",
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
                    "width": 110,
                    "pinned": "left",
                    "renderFn": "cellOnClick",
                    "renderFnParams": {
                        "actionType": "groupBy",
                        "groupBy": {"paramName": "symbol"},
                    },
                },
                {
                    "field": "name",
                    "headerName": "Name",
                    "cellDataType": "text",
                    "width": 200,
                },
                {
                    "field": "type",
                    "headerName": "Type",
                    "cellDataType": "text",
                    "width": 110,
                },
                {
                    "field": "industry",
                    "headerName": "Industry",
                    "cellDataType": "text",
                    "width": 160,
                },
                {
                    "field": "exchange_long",
                    "headerName": "Exchange",
                    "cellDataType": "text",
                    "width": 140,
                },
                {
                    "field": "country",
                    "headerName": "Country",
                    "cellDataType": "text",
                    "width": 90,
                },
            ],
        }
    },
})
@router.get("/entity_search")
def entity_search(search: str = "tesla", countries: str = "us"):
    """Search Marketaux entities (limit fixed at 50 by the API)."""

    def fetch():
        return client.entity_search(search=search, countries=countries)

    try:
        payload = core.cache.get_or_set(
            f"entity_search:{search}:{countries}", fetch, 600,
        )
    except MarketauxError as exc:
        return core.error_response(exc.status_code, exc.code, exc.message)

    return payload.get("data", [])
