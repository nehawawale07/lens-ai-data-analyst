from __future__ import annotations

from typing import Any

import pandas as pd


def chart_from_frame(
    frame: pd.DataFrame,
    chart_type: str,
    title: str,
    x: str | None = None,
    y: str | None = None,
) -> dict[str, Any] | None:
    if frame.empty:
        return None
    columns = list(frame.columns)
    x_col = x if x in columns else columns[0]
    remaining = [col for col in columns if col != x_col]
    y_col = y if y in columns else (remaining[0] if remaining else x_col)
    data = frame.head(200).where(frame.head(200).notna(), None).to_dict(orient="records")
    allowed = {"bar", "line", "pie", "scatter", "area"}
    return {
        "type": chart_type if chart_type in allowed else "bar",
        "title": title,
        "x": x_col,
        "y": y_col,
        "data": data,
    }



def guess_chart_type(question: str) -> str:
    text = question.lower()

    # Respect explicitly requested chart types first.
    if "pie" in text or "share" in text or "proportion" in text:
        return "pie"
    if "scatter" in text or "correlation" in text:
        return "scatter"
    if "area chart" in text or "area graph" in text:
        return "area"
    if "line chart" in text or "line graph" in text:
        return "line"
    if "bar chart" in text or "bar graph" in text:
        return "bar"

    # Infer a line chart for time-based trends.
    if any(term in text for term in ("trend", "over time", "monthly", "daily")):
        return "line"

    return "bar"
