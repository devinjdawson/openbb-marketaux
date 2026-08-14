import sys, json
sys.path.insert(0, "backend")
import main
from main import app, WIDGETS

def collect_paths(app):
    paths = set()
    for r in app.routes:
        router = getattr(r, "original_router", None)
        if router is not None:
            for sub in router.routes:
                if hasattr(sub, "path"):
                    paths.add(sub.path.lstrip("/"))
        elif hasattr(r, "path"):
            paths.add(r.path.lstrip("/"))
    return paths

routes = collect_paths(app)
errors = []
for wid, cfg in WIDGETS.items():
    ep = cfg["endpoint"]
    if ep not in routes:
        errors.append(f"widget {wid}: endpoint {ep} not a route")
    if "name" not in cfg or "type" not in cfg or "gridData" not in cfg:
        errors.append(f"widget {wid}: missing required keys")
    for p in cfg.get("params", []):
        for param in (p if isinstance(p, list) else [p]):
            if "paramName" not in param or "type" not in param:
                errors.append(f"widget {wid}: malformed param {param}")
            if param.get("type") == "endpoint":
                target = param["optionsEndpoint"].lstrip("/")
                if target not in routes:
                    errors.append(f"widget {wid}: optionsEndpoint {target} not a route")

apps = json.load(open("backend/apps.json", encoding="utf-8"))
for appcfg in apps:
    for tab in appcfg["tabs"].values():
        for item in tab["layout"]:
            if item["i"] not in WIDGETS:
                errors.append(f"app layout item {item['i']} not registered")
    for group in appcfg.get("groups", []):
        if group["paramName"] not in {
            param.get("paramName")
            for cfg in WIDGETS.values()
            for p in (cfg.get("params") or [])
            for param in (p if isinstance(p, list) else [p])
        }:
            errors.append(f"group param {group['paramName']} unused by any widget")

print("routes:", sorted(routes))
print("errors:", errors if errors else "none")
assert not errors
print("VALIDATION PASSED")
