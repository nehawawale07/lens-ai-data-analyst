from __future__ import annotations

import re

import pandas as pd

from app.session_store import Session

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|attach|copy|export|pragma|call|create|replace|grant|revoke|load)\b",
    re.IGNORECASE,
)


class SqlError(ValueError):
    pass


def execute_sql(session: Session, sql: str, limit: int = 500) -> pd.DataFrame:
    statement = sql.strip().rstrip(";")
    if not statement:
        raise SqlError("SQL query is empty.")
    if ";" in statement:
        raise SqlError("Only a single SQL statement is allowed.")
    if FORBIDDEN.search(statement):
        raise SqlError("Only read-only SELECT / WITH queries are allowed.")
    if not re.match(r"^(select|with)\b", statement, re.IGNORECASE):
        raise SqlError("Query must start with SELECT or WITH.")

    wrapped = f"SELECT * FROM ({statement}) AS analysis_result LIMIT {limit}"
    conn = session.connection()
    try:
        return conn.execute(wrapped).df()
    except Exception as exc:  # noqa: BLE001
        raise SqlError(str(exc)) from exc
    finally:
        conn.close()


def pandas_equivalent(sql: str) -> str:
    return (
        "# Generated pandas equivalent (illustrative)\n"
        "import pandas as pd\n"
        f"# SQL executed via DuckDB:\n# {sql.strip()}\n"
        "result = duckdb.query(sql).to_df()\n"
        "result.head()"
    )
