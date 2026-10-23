from __future__ import annotations

from typing import Any

import pandas as pd


def quality_report(name: str, frame: pd.DataFrame) -> dict[str, Any]:
    missing = frame.isna().sum()
    duplicate_rows = int(frame.duplicated().sum())
    return {
        "table": name,
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "duplicate_rows": duplicate_rows,
        "missing_by_column": {col: int(val) for col, val in missing.items() if val > 0},
        "numeric_summary": frame.describe(include="number").round(3).to_dict(),
        "categorical_summary": {
            col: frame[col].astype(str).value_counts().head(5).to_dict()
            for col in frame.select_dtypes(exclude="number").columns[:8]
        },
    }
