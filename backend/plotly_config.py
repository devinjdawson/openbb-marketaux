"""Plotly theme helpers for chart widgets."""


def get_theme_colors(theme: str = "dark") -> dict:
    if theme == "dark":
        return {
            "main_line": "#FF8000",
            "secondary_line": "#2D9BF0",
            "positive": "#22C55E",
            "negative": "#EF4444",
            "text": "#FFFFFF",
            "grid": "rgba(51, 51, 51, 0.3)",
            "background": "#151518",
        }
    return {
        "main_line": "#2E5090",
        "secondary_line": "#00AA44",
        "positive": "#22C55E",
        "negative": "#EF4444",
        "text": "#333333",
        "grid": "rgba(221, 221, 221, 0.3)",
        "background": "#FFFFFF",
    }


def base_layout(theme: str = "dark", **kwargs) -> dict:
    colors = get_theme_colors(theme)
    layout = {
        "paper_bgcolor": colors["background"],
        "plot_bgcolor": colors["background"],
        "font": {"color": colors["text"]},
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
        "xaxis": {"gridcolor": colors["grid"], "tickfont": {"color": colors["text"]}},
        "yaxis": {"gridcolor": colors["grid"], "tickfont": {"color": colors["text"]}},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"color": colors["text"]},
        },
    }
    layout.update(kwargs)
    return layout


def get_toolbar_config() -> dict:
    return {
        "displayModeBar": True,
        "responsive": True,
        "scrollZoom": True,
        "modeBarButtonsToRemove": [
            "lasso2d",
            "select2d",
            "autoScale2d",
            "toggleSpikelines",
            "hoverClosestCartesian",
            "hoverCompareCartesian",
        ],
        "doubleClick": "reset+autosize",
        "showTips": False,
        "displaylogo": False,
    }
