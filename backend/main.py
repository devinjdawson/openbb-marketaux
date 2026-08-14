"""
Marketaux Sentiment Backend for OpenBB Workspace

Run the server:
    uvicorn main:app --reload --port 8080
"""

import json

from fastapi.responses import JSONResponse

import core
from core import ROOT_PATH, WIDGETS, app
from widgets_news import router as news_router
from widgets_sentiment import router as sentiment_router
from widgets_market import router as market_router

app.include_router(news_router)
app.include_router(sentiment_router)
app.include_router(market_router)


@app.get("/")
def read_root():
    return {
        "Info": "Marketaux Sentiment Backend for OpenBB Workspace",
        "marketaux_token_configured": bool(core.MARKETAUX_API_TOKEN),
        "widgets": len(WIDGETS),
        "usage_note": "Add /widgets.json as a backend in OpenBB Workspace "
                      "(https://my.openbb.co -> Data Connections).",
    }


@app.get("/widgets.json")
def get_widgets():
    """Widget configuration for the OpenBB Workspace."""
    return WIDGETS


@app.get("/apps.json")
def get_apps():
    """App configuration for the OpenBB Workspace."""
    return JSONResponse(content=json.load((ROOT_PATH / "apps.json").open()))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
