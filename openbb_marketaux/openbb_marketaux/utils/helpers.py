"""HTTP client and helpers for the Marketaux v1 API."""

# pylint: disable=unused-argument

from openbb_core.app.model.abstract.error import OpenBBError
from openbb_core.provider.utils.errors import UnauthorizedError
from openbb_core.provider.utils.helpers import get_querystring, make_request

BASE_URL = "https://api.marketaux.com/v1"
CREDENTIAL_NAME = "marketaux_api_key"


def get_token(credentials: dict | None) -> str:
    """Resolve the Marketaux API key from OpenBB user credentials."""
    if credentials:
        token = credentials.get(CREDENTIAL_NAME)
        if token:
            return str(token)
    raise UnauthorizedError(
        "The Marketaux API key is missing. Set it with "
        "`obb.user.credentials.marketaux_api_key = '***'`, then "
        "`obb.account.save()`. Get a free token at "
        "https://www.marketaux.com/register"
    )


def marketaux_get(path: str, params: dict, token: str, timeout: int = 30) -> dict:
    """Make a GET request against the Marketaux API and parse the response.

    Error bodies returned by Marketaux are surfaced as OpenBB errors.
    The token is never included in raised messages.
    """
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    clean["api_token"] = token
    querystring = get_querystring(clean, exclude=[])
    url = f"{BASE_URL}{path}?{querystring}"

    response = make_request(url, timeout=timeout)

    if response.status_code == 401:
        raise UnauthorizedError("Invalid Marketaux API key.")

    if response.status_code != 200:
        try:
            error = response.json().get("error", {})
        except ValueError:
            error = {}
        code = error.get("code", str(response.status_code))
        message = error.get("message", "Unknown Marketaux API error.")
        if response.status_code == 403 and code == "endpoint_access_restricted":
            message += " This endpoint requires a Marketaux Standard plan or above."
        raise OpenBBError(f"Marketaux request failed ({code}): {message}")

    return response.json()


def split_symbols(symbol: str | list | None) -> str:
    """Normalize a symbol input to an uppercase comma-separated string."""
    if not symbol:
        return ""
    if isinstance(symbol, (list, tuple)):
        items = [str(s).strip().upper() for s in symbol if str(s).strip()]
    else:
        items = [s.strip().upper() for s in str(symbol).split(",") if s.strip()]
    return ",".join(dict.fromkeys(items))
