from __future__ import annotations

import pandas as pd


def schema_text(tables: dict[str, pd.DataFrame]) -> str:
    chunks = []
    for name, frame in tables.items():
        cols = ", ".join(f"{col}:{dtype}" for col, dtype in frame.dtypes.items())
        chunks.append(f"- {name} ({len(frame)} rows): {cols}")
    return "\n".join(chunks) if chunks else "(no tables uploaded)"


def pick_table(tables: dict[str, pd.DataFrame], preferred: str | None = None) -> tuple[str, pd.DataFrame]:
    if preferred and preferred in tables:
        return preferred, tables[preferred]
    name = next(iter(tables))
    return name, tables[name]
