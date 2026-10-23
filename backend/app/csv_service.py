from __future__ import annotations

import io
import re

import pandas as pd

SAFE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class CsvValidationError(ValueError):
    pass


def sanitize_table_name(filename: str, existing: set[str]) -> str:
    stem = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = stem.rsplit(".", 1)[0]
    name = re.sub(r"[^a-zA-Z0-9_]", "_", stem).lower()
    if not name or name[0].isdigit():
        name = f"table_{name}" if name else "table"
    if not SAFE_NAME.match(name):
        name = "dataset"
    candidate = name
    index = 2
    while candidate in existing:
        candidate = f"{name}_{index}"
        index += 1
    return candidate


def load_csv(content: bytes, filename: str, max_bytes: int) -> tuple[pd.DataFrame, list[str]]:
    if len(content) > max_bytes:
        raise CsvValidationError(f"File exceeds the {max_bytes // (1024 * 1024)} MB upload limit.")
    if not filename.lower().endswith(".csv"):
        raise CsvValidationError("Only CSV files are supported.")
    if not content.strip():
        raise CsvValidationError("The uploaded file is empty.")

    warnings: list[str] = []
    last_error: Exception | None = None
    frame: pd.DataFrame | None = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            frame = pd.read_csv(io.BytesIO(content), encoding=encoding)
            break
        except Exception as exc:  # noqa: BLE001 — try the next encoding
            last_error = exc
    if frame is None:
        raise CsvValidationError(f"Could not parse CSV: {last_error}")

    if frame.empty:
        raise CsvValidationError("CSV parsed successfully but contains no rows.")
    if frame.columns.duplicated().any():
        frame.columns = _dedupe_columns(list(frame.columns.astype(str)))
        warnings.append("Duplicate column names were renamed.")

    frame.columns = [str(col).strip() or f"column_{i}" for i, col in enumerate(frame.columns)]
    null_ratio = frame.isna().mean()
    sparse = [col for col, ratio in null_ratio.items() if ratio > 0.4]
    if sparse:
        warnings.append("High missing-value rate in: " + ", ".join(map(str, sparse)))
    return frame, warnings


def _dedupe_columns(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for col in columns:
        count = seen.get(col, 0)
        result.append(col if count == 0 else f"{col}_{count}")
        seen[col] = count + 1
    return result


def profile_frame(name: str, frame: pd.DataFrame, warnings: list[str]) -> dict:
    preview = frame.head(8).where(frame.head(8).notna(), None)
    return {
        "name": name,
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "column_types": {col: str(dtype) for col, dtype in frame.dtypes.items()},
        "preview": preview.to_dict(orient="records"),
        "warnings": warnings,
    }
