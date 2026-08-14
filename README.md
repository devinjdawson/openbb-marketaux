# openbb-marketaux

A Python **FastAPI backend** that connects [Marketaux](https://www.marketaux.com) financial news & sentiment and [Yahoo Finance](https://finance.yahoo.com) market data to **OpenBB Workspace** widgets.

It combines the three references in [.reference/](.reference/):

- **`docs.md`** — the Marketaux API specification (endpoints, parameters, response shapes).
- **`backends-for-openbb/`** — OpenBB's official guide for building Workspace custom backends (CORS, `widgets.json`, `apps.json`, widget types).
- **`Market-Sentiment/`** — the bucketed, Bayesian-adjusted news sentiment methodology from Eric-exe/Market-Sentiment.

## What it does

| Category | Widgets | Source |
| --- | --- | --- |
| News | Market News (search + sentiment filter), Symbol News | Marketaux `/v1/news/all` |
| Sentiment | Sentiment Summary, Sentiment Breakdown, Sentiment History*, Trending Entities* | Marketaux entity sentiment |
| Market data | Quotes, Price Chart, Entity Search | Yahoo Finance (yfinance) + Marketaux entity search |

`*` Sentiment History and Trending Entities use Marketaux `entity/stats/intraday` and `entity/trending/aggregation`, which require a **Standard plan or above**. On the free plan they return a clean `endpoint_access_restricted (403)` error instead of crashing.

## Sentiment methodology

Two complementary approaches are implemented, both driven by Marketaux entity sentiment scores (`-1` to `+1`):

1. **Bucketed Bayesian score** (`Sentiment Breakdown`) — ports the Market-Sentiment project. Articles are counted into six buckets (weak/moderate/strong × positive/negative), then normalised with a Bayesian prior so symbols with little news aren't over-ranked:

   ```
   raw = Σ (pos_count × weight) − Σ (neg_count × weight)
   adjusted = raw / (Σ (pos_count + neg_count) × weight + BAYESIAN_EXTRA_VALUES)
   ```

   Weights: weak = 1, moderate = 2, strong = 3. Ranges: weak `0.15–0.39`, moderate `0.4–0.69`, strong `0.7–1.0`. This costs 6 Marketaux requests per refresh.

2. **Per-symbol entity average** (`Sentiment Summary`) — one request per symbol, averaging the `sentiment_score` of that symbol's identified entities across recent articles (1 request per symbol).

## Project layout

```
backend/
├── main.py               # FastAPI app wiring + widgets.json / apps.json routes
├── core.py               # CORS, widget registry, TTL cache, env config, helpers
├── plotly_config.py      # shared Plotly theme/layout/toolbar helpers
├── apps.json             # OpenBB Workspace app + tab layout definition
├── widgets_news.py       # news feed widgets
├── widgets_sentiment.py  # sentiment table/chart widgets
├── widgets_market.py     # Yahoo Finance + entity search widgets
├── services/
│   ├── marketaux.py      # thin Marketaux v1 API client
│   ├── sentiment.py      # bucket + Bayesian sentiment scoring
│   └── yahoo.py          # yfinance quote/history wrappers
├── requirements.txt
├── .env.example          # copy to .env and fill in your token
└── .env                  # your local config (gitignored)
scripts/
└── validate_backend.py   # sanity-checks widget/route/apps.json integrity
```

## Setup

Requires Python 3.11+.

```powershell
# create + activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r backend\requirements.txt

# configure your Marketaux token (free at https://www.marketaux.com/register)
Copy-Item backend\.env.example backend\.env   # then edit backend\.env
```

Set `MARKETAUX_API_TOKEN` in `backend\.env`. Yahoo Finance (yfinance) needs **no API key**.

> Note: Yahoo Finance has no official free API — `yfinance` queries Yahoo's public endpoints directly, so those endpoints can change without notice.

## Run

```powershell
cd backend
uvicorn main:app --reload --port 8080
# or: ..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8080
```

Then verify:
- `http://localhost:8080/` — health/info
- `http://localhost:8080/widgets.json` — widget definitions
- `http://localhost:8080/apps.json` — app layout

## Connect to OpenBB Workspace

1. Open [OpenBB Workspace](https://my.openbb.co) → **Admin** → **Data Connections** → **My Data** → **Backend**.
2. Add the backend URL: `http://localhost:8080/widgets.json`.
3. The **Market Sentiment** app appears with two tabs (**Overview**, **News**) and all widgets become available in the widget picker.
4. (Optional) Add the backend app via a **Custom Command / App** so the full dashboard loads in one click.

The **Group 1** linkage wires `Symbol News` and `Price Chart` to the shared `symbol` parameter. Clicking a symbol in **Quotes**, **Sentiment Summary**, **Trending Entities**, or **Entity Search** pushes that symbol into the group and updates both widgets at once.

## Widget / endpoint reference

| Endpoint | Type | Description |
| --- | --- | --- |
| `GET /news_market` | newsfeed | Global Marketaux news; `search`, `sentiment`, `language`, `limit` |
| `GET /news_symbol` | newsfeed | News for one symbol; `symbol`, `days`, `limit` |
| `GET /sentiment_summary` | table | Per-symbol entity sentiment; `symbols`, `days` |
| `GET /sentiment_breakdown` | chart | Bucket counts + adjusted score; `symbols`, `days` |
| `GET /sentiment_history` | chart | Sentiment time series (Standard+); `symbols`, `interval`, `days` |
| `GET /trending_entities` | table | Trending entities (Standard+); `countries`, `days`, `limit` |
| `GET /yahoo_quotes` | table | Live Yahoo quotes; `symbols` |
| `GET /yahoo_price_chart` | chart | Price chart w/ volume; `symbol`, `period`, `chart_type` |
| `GET /entity_search` | table | Marketaux entity search; `search`, `countries` |
| `GET /symbol_options` | options | Static symbol dropdown list (no API cost) |

## Configuration (backend/.env)

| Variable | Default | Purpose |
| --- | --- | --- |
| `MARKETAUX_API_TOKEN` | — | Marketaux API token (required) |
| `DEFAULT_SYMBOLS` | `AAPL,MSFT,AMZN,GOOGL,TSLA,NVDA,META` | Default watchlist |
| `SENTIMENT_DAYS` | `7` | Default sentiment lookback (days) |
| `BAYESIAN_EXTRA_VALUES` | `100` | Bayesian prior in adjusted score |
| `CACHE_TTL_NEWS` | `120` | News cache seconds |
| `CACHE_TTL_SENTIMENT` | `900` | Sentiment cache seconds |
| `CACHE_TTL_YAHOO_QUOTES` | `60` | Quote cache seconds |
| `CACHE_TTL_YAHOO_HISTORY` | `300` | History cache seconds |

## Rate limits & caching

Marketaux free tier allows **100 requests/day** and ~60/minute. All upstream calls go through a thread-safe TTL cache (`core.TTLCache`) so repeated widget refreshes don't burn quota. Lower the cache TTLs only if you have a paid plan with higher limits.

## Validation

```powershell
# structural sanity check (routes <-> widgets.json <-> apps.json)
.venv\Scripts\python.exe scripts\validate_backend.py

# official OpenBB validators (server must be running on :8080)
python .reference\backends-for-openbb\scripts\validate_widgets.py <dir>
python .reference\backends-for-openbb\scripts\validate_apps.py <dir>
python .reference\backends-for-openbb\scripts\validate_endpoints.py --base-url http://localhost:8080 <dir>
```
(`<dir>` must contain a `widgets.json` and `apps.json`; fetch `widgets.json` from `http://localhost:8080/widgets.json`.)

## Notes & limitations

- The `.reference/` directory contains read-only reference repos (git submodules) plus the Marketaux docs — do not edit.
- Marketaux returns paginated, grouped news (`group_similar=true` by default). Counts reflect grouped results.
- Yahoo Finance data is delayed and unofficial; treat it as indicative, not trading data.
