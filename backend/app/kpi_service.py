from __future__ import annotations

import math

import pandas as pd


def build_dataset_kpis(name: str, frame: pd.DataFrame) -> dict:
    """Build safe, data-driven KPIs for a complete uploaded dataset."""
    rows, columns = frame.shape
    total_cells = rows * columns
    missing_cells = int(frame.isna().sum().sum())
    duplicate_rows = int(frame.duplicated().sum())

    numeric = frame.select_dtypes(include="number")
    numeric_columns = list(numeric.columns)

    metrics = [
        {
            "label": "Rows",
            "value": rows,
            "format": "integer",
        },
        {
            "label": "Columns",
            "value": columns,
            "format": "integer",
        },
        {
            "label": "Missing cells",
            "value": missing_cells,
            "format": "integer",
        },
        {
            "label": "Duplicate rows",
            "value": duplicate_rows,
            "format": "integer",
        },
    ]

    numeric_summary = []
    for column in numeric_columns[:8]:
        values = numeric[column].dropna()
        if values.empty:
            continue

        total = float(values.sum())
        average = float(values.mean())

        numeric_summary.append({
            "column": str(column),
            "count": int(values.count()),
            "sum": total if math.isfinite(total) else None,
            "mean": average if math.isfinite(average) else None,
        })

    return {
        "name": name,
        "rows": int(rows),
        "columns": int(columns),
        "missing_cells": missing_cells,
        "missing_percentage": round(
            (missing_cells / total_cells) * 100, 2
        ) if total_cells else 0.0,
        "duplicate_rows": duplicate_rows,
        "numeric_column_count": int(len(numeric_columns)),
        "metrics": metrics,
        "numeric_summary": numeric_summary,
    }


def build_session_kpis(tables: dict[str, pd.DataFrame]) -> dict:
    """Return per-dataset KPIs and overall session totals."""
    datasets = [
        build_dataset_kpis(name, frame)
        for name, frame in tables.items()
    ]

    return {
        "dataset_count": len(datasets),
        "total_rows": sum(item["rows"] for item in datasets),
        "total_columns": sum(item["columns"] for item in datasets),
        "total_missing_cells": sum(
            item["missing_cells"] for item in datasets
        ),
        "datasets": datasets,
    }
