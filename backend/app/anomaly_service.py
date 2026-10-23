from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def detect_anomalies(
    frame: pd.DataFrame,
    table_name: str,
    z_threshold: float = 3.0,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    numeric = frame.select_dtypes(include=[np.number])

    if numeric.empty:
        return [
            {
                "table": table_name,
                "column": None,
                "method": "none",
                "reason": "No numeric columns available for statistical anomaly detection.",
                "count": 0,
            }
        ]

    for column in numeric.columns:
        series = numeric[column].dropna()

        if series.nunique() < 5 or len(series) < 8:
            continue

        mean = float(series.mean())
        std = float(series.std())

        if std == 0:
            continue

        zscores = ((series - mean) / std).abs()
        z_mask = zscores >= z_threshold

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        iqr_mask = (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)

        # Count unique rows flagged by either method.
        combined_mask = z_mask | iqr_mask
        z_count = int(z_mask.sum())
        iqr_count = int(iqr_mask.sum())
        combined_count = int(combined_mask.sum())

        if combined_count == 0:
            continue

        # Show the most extreme flagged values, including IQR-only outliers.
        flagged_indices = series[combined_mask].index
        ranked_indices = (
            zscores.loc[flagged_indices]
            .sort_values(ascending=False)
            .head(5)
            .index
        )

        sample_rows = (
            frame.loc[ranked_indices]
            .where(pd.notna(frame.loc[ranked_indices]), None)
            .to_dict(orient="records")
        )

        findings.append(
            {
                "table": table_name,
                "column": str(column),
                "method": f"z-score (>= {z_threshold}) and IQR",
                "count": combined_count,
                "z_score_count": z_count,
                "iqr_count": iqr_count,
                "mean": round(mean, 4),
                "std": round(std, 4),
                "reason": (
                    f"{column} has potential outliers (mean {mean:.2f}, "
                    f"standard deviation {std:.2f}). "
                    f"{z_count} rows exceed |z| >= {z_threshold}; "
                    f"{iqr_count} fall outside the 1.5xIQR range. "
                    f"{combined_count} unique rows are flagged by at least one method. "
                    "Review the sample rows before deciding whether these are errors "
                    "or legitimate unusual values."
                ),
                "sample_rows": sample_rows,
            }
        )

    if not findings:
        findings.append(
            {
                "table": table_name,
                "column": None,
                "method": "z-score/IQR",
                "count": 0,
                "reason": "No statistical outliers were flagged at the current thresholds.",
            }
        )

    return findings
