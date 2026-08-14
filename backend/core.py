"""
Core components shared by all widget modules.

- FastAPI application with CORS configured for OpenBB Workspace
- Widget registry (WIDGETS dict + register_widget decorator)
- Environment configuration
- TTL cache with per-key in-flight deduplication
  (Marketaux free tier allows 100 requests/day)
"""

import asyncio
import hashlib
import os
import threading
import time
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT_PATH = Path(__file__).parent.resolve()

load_dotenv(ROOT_PATH / ".env")


def _int_env(name: str, default: int) -> int:
    """Parse an integer env var, falling back on missing/invalid values."""
    raw = os.getenv(name, "")
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return default


MARKETAUX_API_TOKEN = os.getenv("MARKETAUX_API_TOKEN", "")

DEFAULT_SYMBOLS = os.getenv("DEFAULT_SYMBOLS", "AAPL,MSFT,AMZN,GOOGL,TSLA,NVDA,META")
SENTIMENT_DAYS = _int_env("SENTIMENT_DAYS", 7)
BAYESIAN_EXTRA_VALUES = _int_env("BAYESIAN_EXTRA_VALUES", 100)

CACHE_TTL_NEWS = _int_env("CACHE_TTL_NEWS", 120)
CACHE_TTL_SENTIMENT = _int_env("CACHE_TTL_SENTIMENT", 900)
CACHE_TTL_YAHOO_QUOTES = _int_env("CACHE_TTL_YAHOO_QUOTES", 60)
CACHE_TTL_YAHOO_HISTORY = _int_env("CACHE_TTL_YAHOO_HISTORY", 300)

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

# Single source of truth for what "positive"/"negative" means across the
# backend: the weak-bucket boundaries from the Market-Sentiment methodology.
SENTIMENT_POSITIVE_THRESHOLD = SENTIMENT_RANGES["weak"][0]
SENTIMENT_NEGATIVE_THRESHOLD = -SENTIMENT_RANGES["weak"][0]


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
    """Thread-safe in-memory cache with per-entry TTL.

    Concurrent misses for the same key run the producer only once;
    other callers wait for the in-flight result.
    """

    def __init__(self, maxsize: int = 512):
        self._data = {}
        self._inflight = {}
        self._lock = threading.Lock()
        self._maxsize = maxsize

    def get_or_set(self, key, producer, ttl):
        now = time.time()
        owner = True

        with self._lock:
            entry = self._data.get(key)
            if entry is not None and entry[0] > now:
                return entry[1]

            event = self._inflight.get(key)
            if event is None:
                event = threading.Event()
                self._inflight[key] = event
            else:
                owner = False

        if not owner:
            event.wait()
            with self._lock:
                entry = self._data.get(key)
            if entry is not None:
                return entry[1]
            # The owner's producer failed; retry as the sole producer.
            return self.get_or_set(key, producer, ttl)

        try:
            value = producer()
        except Exception:
            with self._lock:
                self._inflight.pop(key, None)
            event.set()
            raise

        with self._lock:
            self._inflight.pop(key, None)
            self._data.pop(key, None)
            self._data[key] = (time.time() + ttl, value)
            self._evict_locked()
        event.set()
        return value

    def _evict_locked(self):
        now = time.time()
        expired = [k for k, (expires, _) in self._data.items() if expires <= now]
        for key in expired:
            del self._data[key]
        while len(self._data) > self._maxsize:
            oldest = next(iter(self._data))
            del self._data[oldest]


cache = TTLCache()


def resolve_marketaux_token(
    marketaux_api_key: str = Query(default=""),
    marketaux_api_key_header: str = Header(default="", alias="marketaux-api-key"),
    marketaux_api_key_header_us: str = Header(
        default="", alias="marketaux_api_key", convert_underscores=False
    ),
) -> str:
    """Marketaux token resolution: per-request key (query param or header as
    configured in the OpenBB Workspace backend connection) takes precedence
    over the MARKETAUX_API_TOKEN environment variable."""
    return (
        marketaux_api_key
        or marketaux_api_key_header
        or marketaux_api_key_header_us
        or MARKETAUX_API_TOKEN
    )


MarketauxToken = Depends(resolve_marketaux_token)


def token_hash(token: str) -> str:
    """Short non-reversible token identifier for cache keys."""
    if not token:
        return "none"
    return hashlib.sha256(token.encode()).hexdigest()[:10]


def split_symbols(symbols: str) -> list:
    """Split a comma separated symbol string into a clean uppercase list."""
    return [s.strip().upper() for s in symbols.split(",") if s.strip()]


def normalize_symbols(symbols) -> list:
    """Deduplicate and sort symbols so cache keys are order-insensitive."""
    return sorted(set(symbols))


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
