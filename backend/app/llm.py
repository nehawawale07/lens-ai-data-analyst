from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": "List uploaded tables, columns, and dtypes.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "Run a read-only DuckDB SQL SELECT/WITH query against uploaded CSVs as tables.",
            "parameters": {
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "Build a chart from a SQL query result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "scatter", "area"]},
                    "title": {"type": "string"},
                    "x": {"type": "string"},
                    "y": {"type": "string"},
                },
                "required": ["sql", "chart_type", "title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_anomalies",
            "description": "Flag statistical outliers in numeric columns and explain them.",
            "parameters": {
                "type": "object",
                "properties": {"table": {"type": "string"}},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "data_quality",
            "description": "Return missing values, duplicates, and summary stats.",
            "parameters": {
                "type": "object",
                "properties": {"table": {"type": "string"}},
                "additionalProperties": False,
            },
        },
    },
]


SYSTEM_PROMPT = """You are Lens, a production-minded AI data analyst.
You help users understand uploaded CSV tables using tools.
Rules:
- Always inspect schema before writing SQL if you are unsure of column names.
- Prefer DuckDB SQL. Quote mixed-case column names.
- When a visualization would help, call create_chart.
- For anomaly questions, call detect_anomalies and explain why rows were flagged.
- Keep answers concise, business-oriented, and cite numbers from tool results.
- After tools finish, explain your reasoning in 2-4 sentences.
- If you generate SQL, include it in the final answer in a sql code fence.
"""


def chat(messages: list[dict[str, Any]]) -> dict[str, Any]:
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.1,
    }
    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def parse_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    calls = message.get("tool_calls") or []
    parsed = []
    for call in calls:
        function = call.get("function") or {}
        args = function.get("arguments") or "{}"
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        parsed.append(
            {
                "id": call.get("id"),
                "name": function.get("name"),
                "arguments": args,
            }
        )
    return parsed
