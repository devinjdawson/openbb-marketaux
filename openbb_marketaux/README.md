# OpenBB Marketaux Extension

Marketaux news sentiment & analytics provider extension for the [OpenBB Platform](https://docs.openbb.co/platform).

## Install

```bash
pip install -e .
```

## Credentials

Get a free token at https://www.marketaux.com/register, then:

```python
obb.user.credentials.marketaux_api_key = "your_token"
obb.account.save()
```

## Commands

Standard models (usable wherever these models exist):

```python
obb.news.company(symbol="AAPL,TSLA", provider="marketaux")
obb.news.world(provider="marketaux", sentiment="positive")
obb.equity.search(query="tesla", provider="marketaux")
```

Marketaux-specific models:

```python
obb.marketaux.trending(countries="us", provider="marketaux")
obb.marketaux.sentiment(symbol="AAPL,TSLA,NVDA", provider="marketaux")
obb.marketaux.sentiment_breakdown(symbol="TSLA", provider="marketaux")
obb.marketaux.sentiment_history(symbol="AAPL,TSLA", interval="day", provider="marketaux")
```

Note: `sentiment_history` (and trending) rely on Marketaux endpoints that require a Standard plan or above on the Marketaux side. `sentiment` and `sentiment_breakdown` work on the free plan.

## Methodology

`sentiment_breakdown` ports the Market-Sentiment bucketed Bayesian score: articles are counted into six sentiment buckets (weak/moderate/strong × positive/negative, weights 1/2/3) and normalised with a Bayesian prior of 100 so low-coverage symbols are not over-ranked.
