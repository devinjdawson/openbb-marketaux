"""Smoke test the openbb-marketaux extension inside the OpenBB SDK."""
import warnings

warnings.filterwarnings("ignore")

from openbb import obb  # noqa: E402

print("import OK")
print("has obb.marketaux:", hasattr(obb, "marketaux"))

if hasattr(obb, "marketaux"):
    commands = [c for c in dir(obb.marketaux) if not c.startswith("_")]
    print("obb.marketaux commands:", sorted(commands))

from openbb_core.app.provider_interface import ProviderInterface  # noqa: E402

pif = ProviderInterface()
models = [
    "CompanyNews",
    "WorldNews",
    "EquitySearch",
    "TrendingEntities",
    "SentimentSummary",
    "SentimentBreakdown",
    "SentimentHistory",
]
for model in models:
    providers = list(pif.map.get(model, {}).keys())
    print(f"  {model}: marketaux={'marketaux' in providers} providers={providers}")

providers_list = getattr(obb, "providers", None)
if providers_list is not None:
    print("marketaux provider exposed:", "marketaux" in str(providers_list))

creds_fields = list(type(obb.user.credentials).model_fields.keys())
print("credentials include marketaux_api_key:", "marketaux_api_key" in creds_fields)
