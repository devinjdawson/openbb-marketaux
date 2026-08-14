# openbb-marketaux

Marketaux financial news & market sentiment integration for **OpenBB**, built from the references in [.reference/](.reference/):

- **`docs.md`** — the Marketaux API specification (endpoints, parameters, response shapes).
- **`backends-for-openbb/`** — OpenBB's official guide for Workspace custom backends.
- **`Market-Sentiment/`** — the bucketed, Bayesian-adjusted news sentiment methodology from Eric-exe/Market-Sentiment.

Two deliverables live in this repo:

| Path | What it is | Status |
| --- | --- | --- |
| [`openbb_marketaux/`](openbb_marketaux/) | **OpenBB Platform extension** — Marketaux as a native OpenBB provider (`obb.marketaux`, `obb.news.*`, `obb.equity.search`) | Primary |
| [`backend/`](backend/) | FastAPI custom backend for OpenBB Workspace widgets | Alternative / legacy |

## OpenBB Platform extension (primary)

Install into any environment that has the OpenBB Platform:

```bash
pip install -e .
```

Credentials — use the same `marketaux_api_key` you already entered in OpenBB
(free token at <https://www.marketaux.com/register>):

```python
obb.user.credentials.marketaux_api_key = "***"
obb.account.save()
```

### Commands

Standard models (Marketaux joins the existing provider lists):

```python
obb.news.company(symbol="TSLA", provider="marketaux")        # entity news + sentiment
obb.news.world(provider="marketaux", sentiment="positive")   # global finance news
obb.equity.search(query="tesla", provider="marketaux")       # entity metadata
```

Marketaux-specific commands:

```python
obb.marketaux.trending(countries="us", provider="marketaux")
obb.marketaux.sentiment(symbol="AAPL,TSLA,NVDA", provider="marketaux")
obb.marketaux.sentiment_breakdown(symbol="TSLA", provider="marketaux")
obb.marketaux.sentiment_history(symbol="AAPL,TSLA", interval="day", provider="marketaux")
```

Plan notes (Marketaux side):

- Free/Essential plans: `news.company`, `news.world`, `equity.search`, `marketaux.sentiment`, `marketaux.sentiment_breakdown`.
- Standard+ plans: `marketaux.trending`, `marketaux.sentiment_history` (other plans get a clear `endpoint_access_restricted` error, not a crash).

### Sentiment methodology

Every article/entity carries Marketaux's native sentiment score (-1 to +1), surfaced as `sentiment`/`sentiment_label` columns.

`sentiment_breakdown` additionally ports the Market-Sentiment bucketed Bayesian score: articles are counted into six buckets (weak/moderate/strong × positive/negative, weights 1/2/3) and normalised with a Bayesian prior of 100 so low-coverage symbols are not over-ranked. Costs 6 API requests per call; `sentiment` costs one request per symbol.

### Development & tests

```bash
python scripts/test_extension_load.py       # provider/router/credentials wiring
python scripts/test_extension_fetchers.py   # fetcher pipelines (mocked payloads)
```

## FastAPI Workspace backend (alternative)

See [`backend/README.md`](backend/README.md) — a standalone FastAPI server that feeds OpenBB Workspace widgets over HTTP via `widgets.json`. Useful when you want dashboard widgets without installing the OpenBB Platform.

## Repo notes

- `.reference/` contains read-only reference repos (git submodules) plus the Marketaux docs — do not edit.
- Yahoo Finance is intentionally not part of the extension: the OpenBB Platform already ships `openbb-yfinance` (`obb.equity.price.quote(provider="yfinance")` etc.). The `backend/` alternative includes Yahoo widgets for completeness.
