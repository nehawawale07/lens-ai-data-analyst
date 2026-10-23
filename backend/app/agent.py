from __future__ import annotations

import json
from typing import Any

from app.anomaly_service import detect_anomalies
from app.chart_service import chart_from_frame
from app.config import settings
from app.llm import SYSTEM_PROMPT, chat, parse_tool_calls
from app.local_analyst import analyze as local_analyze
from app.quality_service import quality_report
from app.schema_utils import schema_text
from app.session_store import Session
from app.sql_service import SqlError, execute_sql, pandas_equivalent


def run_agent(session: Session, user_message: str) -> dict[str, Any]:
    if not settings.llm_enabled:
        result = local_analyze(session, user_message)
        result["llm_mode"] = "local"
        _remember(session, user_message, result["answer"])
        return result

    try:
        result = _llm_loop(session, user_message)
        result["llm_mode"] = "llm"
        _remember(session, user_message, result["answer"])
        return result
    except Exception as exc:  # noqa: BLE001
        result = local_analyze(session, user_message)
        result["llm_mode"] = "local-fallback"
        result["reasoning"] = f"LLM call failed ({exc}). Fell back to the local analyst. " + result["reasoning"]
        _remember(session, user_message, result["answer"])
        return result


def _llm_loop(session: Session, user_message: str) -> dict[str, Any]:
    state: dict[str, Any] = {
        "sql": None,
        "pandas_code": None,
        "chart": None,
        "anomalies": [],
        "tables_used": list(session.tables),
    }
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nSchema:\n" + schema_text(session.tables)},
        *session.history,
        {"role": "user", "content": user_message},
    ]

    for _ in range(settings.max_agent_steps):
        payload = chat(messages)
        choice = payload["choices"][0]["message"]
        tool_calls = parse_tool_calls(choice)
        if not tool_calls:
            answer = choice.get("content") or "I could not produce an answer."
            return {
                "answer": answer,
                "reasoning": "The model used tool results (if any) and composed a final explanation.",
                **state,
            }

        messages.append(choice)
        for call in tool_calls:
            observation = _dispatch(session, call["name"], call.get("arguments") or {}, state)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(observation, default=str)[:12000],
                }
            )

    result = local_analyze(session, user_message)
    result["reasoning"] = "Agent reached the step limit; local analyst completed the request. " + result["reasoning"]
    return result


def _dispatch(session: Session, name: str, args: dict[str, Any], state: dict[str, Any]) -> Any:
    if name == "get_schema":
        return {"schema": schema_text(session.tables), "tables": list(session.tables)}

    if name == "execute_sql":
        sql = str(args.get("sql") or "")
        try:
            frame = execute_sql(session, sql)
        except SqlError as exc:
            return {"error": str(exc)}
        state["sql"] = sql
        state["pandas_code"] = pandas_equivalent(sql)
        return {
            "sql": sql,
            "rows": frame.head(40).to_dict(orient="records"),
            "columns": list(frame.columns),
            "row_count": int(len(frame)),
        }

    if name == "create_chart":
        sql = str(args.get("sql") or "")
        try:
            frame = execute_sql(session, sql)
        except SqlError as exc:
            return {"error": str(exc)}
        state["sql"] = sql
        state["pandas_code"] = pandas_equivalent(sql)
        chart = chart_from_frame(
            frame,
            str(args.get("chart_type") or "bar"),
            str(args.get("title") or "Chart"),
            args.get("x"),
            args.get("y"),
        )
        state["chart"] = chart
        return {"ok": True, "chart_preview_rows": len(frame)}

    if name == "detect_anomalies":
        table = args.get("table")
        targets = {table: session.tables[table]} if table in session.tables else session.tables
        findings = []
        for table_name, frame in targets.items():
            findings.extend(detect_anomalies(frame, table_name))
        state["anomalies"] = findings
        return findings

    if name == "data_quality":
        table = args.get("table")
        targets = {table: session.tables[table]} if table in session.tables else session.tables
        return [quality_report(n, f) for n, f in targets.items()]

    return {"error": f"Unknown tool {name}"}


def _remember(session: Session, user_message: str, answer: str) -> None:
    session.history.append({"role": "user", "content": user_message})
    session.history.append({"role": "assistant", "content": answer[:4000]})
    session.history = session.history[-16:]
