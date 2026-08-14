"""Yahoo Finance market data via yfinance (free, no API key required).

Note: Yahoo Finance has no official free API; yfinance queries Yahoo's
public endpoints directly, so endpoints may change without notice.
"""

import math

import yfinance as yf

import core


def _safe(value):
    """Convert numpy scalars / NaN to JSON-friendly values."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        return value.item()
    except AttributeError:
        return value


def get_quotes(symbols: list) -> list:
    """Live quote summary for a list of symbols."""

    def fetch():
        rows = []
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            try:
                info = ticker.fast_info
                last_price = _safe(info.get("lastPrice"))
                previous_close = _safe(info.get("regularMarketPreviousClose"))
                if previous_close is None:
                    previous_close = _safe(info.get("previousClose"))
                change = None
                change_pct = None
                if last_price is not None and previous_close:
                    change = round(last_price - previous_close, 4)
                    change_pct = round((last_price - previous_close) / previous_close * 100, 2)

                name = symbol
                try:
                    name = ticker.info.get("shortName") or symbol
                except Exception:
                    pass

                rows.append({
                    "symbol": symbol,
                    "name": name,
                    "price": last_price,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": _safe(info.get("lastVolume")),
                    "market_cap": _safe(info.get("marketCap")),
                    "day_high": _safe(info.get("dayHigh")),
                    "day_low": _safe(info.get("dayLow")),
                    "week52_high": _safe(info.get("yearHigh")),
                    "week52_low": _safe(info.get("yearLow")),
                    "currency": info.get("currency"),
                })
            except Exception:
                rows.append({"symbol": symbol, "name": symbol, "price": None,
                             "change": None, "change_pct": None, "volume": None,
                             "market_cap": None, "day_high": None, "day_low": None,
                             "week52_high": None, "week52_low": None, "currency": None})
        return rows

    key = "yahoo:quotes:" + ",".join(symbols)
    return core.cache.get_or_set(key, fetch, core.CACHE_TTL_YAHOO_QUOTES)


def get_history(symbol: str, period: str = "3mo", interval: str = "1d") -> list:
    """OHLCV history bars for a symbol."""

    def fetch():
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df is None or df.empty:
            return []
        df = df.reset_index()
        date_col = "Datetime" if "Datetime" in df.columns else "Date"
        bars = []
        for _, row in df.iterrows():
            bars.append({
                "date": row[date_col].isoformat(),
                "open": _safe(row.get("Open")),
                "high": _safe(row.get("High")),
                "low": _safe(row.get("Low")),
                "close": _safe(row.get("Close")),
                "volume": _safe(row.get("Volume")),
            })
        return bars

    key = f"yahoo:history:{symbol}:{period}:{interval}"
    return core.cache.get_or_set(key, fetch, core.CACHE_TTL_YAHOO_HISTORY)
