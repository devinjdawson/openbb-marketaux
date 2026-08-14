"""Client for the Marketaux v1 API (https://www.marketaux.com/documentation)."""

import requests

import core

BASE_URL = "https://api.marketaux.com/v1"
REQUEST_TIMEOUT = 30


class MarketauxError(Exception):
    """Raised when a Marketaux API request fails."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message


class MarketauxClient:
    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> dict:
        token = core.MARKETAUX_API_TOKEN
        if not token:
            raise MarketauxError(
                401,
                "missing_api_token",
                "MARKETAUX_API_TOKEN is not set. Add it to backend/.env "
                "(free token at https://www.marketaux.com/register).",
            )

        clean = {k: v for k, v in params.items() if v not in (None, "")}
        clean["api_token"] = token

        try:
            response = requests.get(
                f"{BASE_URL}{path}", params=clean, timeout=self.timeout
            )
        except requests.RequestException as exc:
            # Never forward str(exc): requests exceptions embed the full URL,
            # which would leak the api_token query parameter to clients.
            raise MarketauxError(
                502, "request_failed",
                f"Upstream request to Marketaux failed ({type(exc).__name__}).",
            ) from exc

        if response.status_code != 200:
            try:
                error = response.json().get("error", {})
            except ValueError:
                error = {}
            raise MarketauxError(
                response.status_code,
                error.get("code", "unknown_error"),
                error.get("message", response.text or "Marketaux request failed."),
            )

        return response.json()

    def news_all(self, **params) -> dict:
        return self._get("/news/all", params)

    def entity_stats_intraday(self, **params) -> dict:
        return self._get("/entity/stats/intraday", params)

    def trending_aggregation(self, **params) -> dict:
        return self._get("/entity/trending/aggregation", params)

    def entity_search(self, **params) -> dict:
        return self._get("/entity/search", params)


client = MarketauxClient()
