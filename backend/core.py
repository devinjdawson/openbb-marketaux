"""
Core components shared by all widget modules.

- FastAPI application with CORS configured for OpenBB Workspace
- Widget registry (WIDGETS dict + register_widget decorator)
- Environment configuration
- Simple TTL cache (Marketaux free tier allows 100 requests/day)
"""

import asyncio
import os
import threading
import time
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT_PATH = Path(__file__).parent.resolve()

load_dotenv(ROOT_PATH / ".env")

MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN", "")

DEFAULT_SYMBOLS = os.getenv("DEFAULT_SYMBOLS", "AAPL,MSFT,AMZN,GOOGL,TSLA,NVDA,META")
SENTIMENT_DAYS = int(os.getenv("SENTIMENT_DAYS", "7"))
BAYESIAN_EXTRA_VALUES = int(os.getenv("BAYESIAN_EXTRA_VALUES", "100"))

CACHE_TTL_NEWS = int(os.getenv("CACHE_TTL_NEWS", "120"))
CACHE_TTL_SENTIMENT = int(os.getenv("CACHE_TTL_SENTIMENT", "900"))
CACHE_TTL_YAHOO_QUOTES = int(os.getenv("CACHE_TTL_YAHOO_QUOTES", "60"))
CACHE_TTL_YAHOO_HISTORY = int(os.getenv("CACHE_TTL_YAHOO_HISTORY", "300"))

SENTIMENT_RANGES = {
    "weak": (0.15, 0.39),
    "moderate": (0.4, 0.69),
    "strong": (0.7, 1.0),
}

SENTIMENT_WEIGHTS = {
    "weak": 1,
    "moderate": 2,
    "strong": 3,
}


app = FastAPI(
    title="Marketaux Sentiment Backend",
    description="Marketaux news & market sentiment backend for OpenBB Workspace",
    version="0.1.0",
)

origins = [
    "https://pro.openbb.co",
    "https://my.openbb.co",
    "https://excel.openbb.co",
    "http://localhost:1420",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


WIDGETS = {}


def register_widget(widget_config):
    """Register a widget configuration in the WIDGETS dictionary."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        endpoint = widget_config.get("endpoint")
        if endpoint:
            if "widgetId" not in widget_config:
                widget_config["widgetId"] = endpoint
            WIDGETS[widget_config["widgetId"]] = widget_config

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class TTLCache:
    """Thread-safe in-memory cache with per-entry time-to-live."""

    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def get_or_set(self, key, producer, ttl):
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if entry is not None and entry[0] > now:
                return entry[1]

        value = producer()

        with self._lock:
            self._data[key] = (now + ttl, value)
            expired = [k for k, (exp, _) in self._data.items() if exp <= now]
            for k in expired:
                del self._data[k]

        return value

    def clear(self):
        with self._lock:
            self._data.clear()


cache = TTLCache()


def split_symbols(symbols: str) -> list:
    """Split a comma separated symbol string into a clean uppercase list."""
    return [s.strip().upper() for s in symbols.split(",") if s.strip()]


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
