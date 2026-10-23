from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    name: str
    rows: int
    columns: int
    column_types: dict[str, str]
    preview: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)


class ChartSpec(BaseModel):
    type: Literal["bar", "line", "pie", "scatter", "area"] = "bar"
    title: str = "Chart"
    x: str
    y: str
    data: list[dict[str, Any]] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    reasoning: str = ""
    sql: str | None = None
    pandas_code: str | None = None
    chart: ChartSpec | None = None
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    tables_used: list[str] = Field(default_factory=list)
    llm_mode: str = "local"
