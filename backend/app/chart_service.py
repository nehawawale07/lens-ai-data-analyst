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
    if "pie" in text or "share" in text or "proportion" in text:
        return "pie"
    if "scatter" in text or "correlation" in text:
        return "scatter"
    if "trend" in text or "over time" in text or "monthly" in text or "daily" in text:
        return "line"
    if "area" in text:
        return "area"
    return "bar"
