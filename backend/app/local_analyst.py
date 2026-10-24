from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.anomaly_service import detect_anomalies
from app.chart_service import chart_from_frame, guess_chart_type
from app.quality_service import quality_report
from app.schema_utils import pick_table, schema_text
from app.session_store import Session
from app.sql_service import SqlError, execute_sql, pandas_equivalent


def _col(frame: pd.DataFrame, *candidates: str) -> str | None:
    lower = {str(col).lower(): col for col in frame.columns}
    for name in candidates:
        if name in lower:
            return lower[name]
        for key, original in lower.items():
            if name in key:
                return original
    return None


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def analyze(session: Session, question: str) -> dict[str, Any]:
    if not session.tables:
        return {
            "answer": "Upload at least one CSV file before asking questions.",
            "reasoning": "No datasets are registered in this session.",
            "sql": None,
            "pandas_code": None,
            "chart": None,
            "anomalies": [],
            "tables_used": [],
        }

    text = question.lower()
    tables_used = list(session.tables)
    name, frame = pick_table(session.tables)

    # For regional revenue questions, prefer a table containing both
    # a region-like column and a revenue-like column.
    if "region" in text and any(term in text for term in ("revenue", "sales", "amount")):
        for candidate_name, candidate_frame in session.tables.items():
            candidate_region = _col(candidate_frame, "region", "country", "state", "area")
            candidate_revenue = _col(candidate_frame, "revenue", "sales", "amount", "total", "price")
            if candidate_region and candidate_revenue:
                name, frame = candidate_name, candidate_frame
                break

    if any(term in text for term in ("monthly", "trend")):
        for candidate_name, candidate_frame in session.tables.items():
            candidate_date = _col(candidate_frame, "order_date", "date", "month", "timestamp")
            candidate_revenue = _col(candidate_frame, "revenue", "sales", "amount", "total", "price")
            if candidate_date and candidate_revenue:
                name, frame = candidate_name, candidate_frame
                break

    # Customer-ranking questions need transaction data with customer and revenue columns.
    if "customer" in text and any(term in text for term in ("top", "highest", "most", "revenue", "spend")):
        for candidate_name, candidate_frame in session.tables.items():
            candidate_customer = _col(candidate_frame, "customer", "client", "account")
            candidate_revenue = _col(candidate_frame, "revenue", "sales", "amount", "total", "price")
            if candidate_customer and candidate_revenue:
                name, frame = candidate_name, candidate_frame
                break

    # Product performance questions should use a table containing
    # both product names and a revenue-like numeric measure.
    if any(term in text for term in ("underperform", "worst", "product")):
        for candidate_name, candidate_frame in session.tables.items():
            candidate_product = _col(candidate_frame, "product", "item", "sku")
            candidate_revenue = _col(candidate_frame, "revenue", "sales", "amount", "total", "price")
            if candidate_product and candidate_revenue:
                name, frame = candidate_name, candidate_frame
                break

    sql = None
    chart = None
    anomalies: list[dict[str, Any]] = []
    reasoning = []

    if any(word in text for word in ("anomal", "outlier", "unusual")):
        reasoning.append("Intent classified as anomaly detection; running z-score and IQR checks.")
        anomalies = []
        for table_name, table in session.tables.items():
            anomalies.extend(detect_anomalies(table, table_name))
        flagged = [item for item in anomalies if item.get("count")]
        if flagged:
            lines = [
                f"- {item['column']} in `{item['table']}`: {item['reason']}"
                for item in flagged
            ]
            answer = "Anomalies were flagged in numeric columns:\n" + "\n".join(lines)
        else:
            answer = "No statistical outliers were flagged with |z| >= 3 or 1.5Ã—IQR."
        return _pack(answer, reasoning, sql, chart, anomalies, tables_used)

    if "quality" in text or "missing" in text or "duplicate" in text:
        reasoning.append("Intent classified as data-quality review.")
        reports = [quality_report(n, t) for n, t in session.tables.items()]
        lines = []
        for report in reports:
            missing = report["missing_by_column"] or "none"
            lines.append(
                f"`{report['table']}`: {report['rows']} rows, {report['duplicate_rows']} duplicate rows, missing={missing}"
            )
        return _pack("Data quality summary:\n" + "\n".join(lines), reasoning, None, None, [], tables_used)

    if "schema" in text or "column" in text and "what" in text:
        reasoning.append("User asked for schema/context of uploaded files.")
        return _pack("Available tables:\n" + schema_text(session.tables), reasoning, None, None, [], tables_used)

    region = _col(frame, "region", "country", "state", "area")
    revenue = _col(frame, "revenue", "sales", "amount", "total", "price")
    product = _col(frame, "product", "item", "sku")
    customer = _col(frame, "customer", "client", "account")
    date_col = _col(frame, "order_date", "date", "month", "timestamp")
    quantity = _col(frame, "quantity", "qty", "units")

    wants_sql = "sql" in text
    wants_chart = any(word in text for word in ("chart", "plot", "visual", "show", "trend", "graph"))
    wants_chart = wants_chart or ("highest" in text or "most" in text or "maximum" in text) and any(term in text for term in ("revenue", "sales", "amount")) and region is not None and revenue is not None

    if "customer" in text and any(term in text for term in ("top", "highest", "most", "revenue", "spend")) and customer and revenue:
        limit = 5
        match = re.search(r"top\s+(\d+)", text)
        if match:
            limit = max(1, min(int(match.group(1)), 100))
        sql = (
            f"SELECT {_quote(customer)} AS customer, SUM({_quote(revenue)}) AS total_revenue "
            f"FROM {_quote(name)} GROUP BY 1 ORDER BY total_revenue DESC LIMIT {limit}"
        )
        reasoning.append(f"Aggregating revenue by customer and returning the top {limit}.")

    elif (
        ("highest" in text or "most" in text or "maximum" in text)
        and any(term in text for term in ("revenue", "sales", "amount"))
        and region
        and revenue
    ):
        sql = (
            f"SELECT {_quote(region)} AS region, SUM({_quote(revenue)}) AS total_revenue "
            f"FROM {_quote(name)} GROUP BY 1 ORDER BY total_revenue DESC"
        )
        reasoning.append("Aggregating revenue by region and ranking descending.")
    elif ("underperform" in text or "worst" in text) and product and revenue:
        sql = (
            f"SELECT {_quote(product)} AS product, SUM({_quote(revenue)}) AS total_revenue "
            f"FROM {_quote(name)} GROUP BY 1 ORDER BY total_revenue ASC LIMIT 10"
        )
        reasoning.append("Ranking products by lowest total revenue as a proxy for underperformance.")
    elif ("monthly" in text or "trend" in text) and date_col and revenue:
        sql = (
            f"SELECT strftime(try_strptime(CAST({_quote(date_col)} AS VARCHAR), "
            f"['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%Y-%m']), '%Y-%m') AS month, "
            f"SUM({_quote(revenue)}) AS total_revenue "
            f"FROM {_quote(name)} "
            f"WHERE try_strptime(CAST({_quote(date_col)} AS VARCHAR), "
            f"['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%Y-%m']) IS NOT NULL "
            f"GROUP BY 1 ORDER BY 1"
        )
        reasoning.append("Parsing dates, grouping revenue by month, and ordering months chronologically.")
        wants_chart = True
    elif "insight" in text or "summar" in text or "overview" in text:
        reasoning.append("Building a descriptive business summary from profile statistics.")
        answer = _summary(session)
        chart = _default_chart(frame, name, region, revenue, date_col)
        return _pack(answer, reasoning, None, chart, [], tables_used)
    else:
        if revenue and region:
            sql = (
                f"SELECT {_quote(region)} AS dimension, SUM({_quote(revenue)}) AS total_revenue "
                f"FROM {name} GROUP BY 1 ORDER BY total_revenue DESC LIMIT 15"
            )
            reasoning.append("Fallback: revenue breakdown by the best available dimension.")
        else:
            cols = ", ".join(_quote(col) for col in frame.columns[:6])
            sql = f"SELECT {cols} FROM {name} LIMIT 20"
            reasoning.append("Fallback: preview of the primary table because the question did not match a known metric.")

    try:
        result = execute_sql(session, sql) if sql else pd.DataFrame()
    except SqlError as exc:
        return _pack(f"SQL failed: {exc}", reasoning, sql, None, [], tables_used)

    if wants_chart or "show" in text or "trend" in text:
        chart = chart_from_frame(result, guess_chart_type(question), question.strip().rstrip("?"), result.columns[0] if len(result.columns) else None, result.columns[1] if len(result.columns) > 1 else None)

    answer_lines = [f"Analyzed `{name}` ({len(frame)} rows)."]

    if ("underperform" in text or "worst" in text) and product and revenue:
        answer_lines.append(
            "Products ranked from lowest total revenue to highest. "
            "Low revenue is only a proxy for underperformance; this analysis "
            "does not account for costs, profit margins, demand, inventory, "
            "or business targets."
        )

    if not result.empty:
        if (
            ("highest" in text or "most" in text or "maximum" in text)
            and any(term in text for term in ("revenue", "sales", "amount"))
            and not any(term in text for term in ("underperform", "worst"))
            and len(result.columns) >= 2
        ):
            first = result.iloc[0]
            dimension_name = str(result.columns[0])
            metric_name = str(result.columns[1])
            answer_lines.append(
                f"**{first[dimension_name]} generated the highest total revenue: "
                f"{first[metric_name]:,.2f}.**"
            )
            if "customer" in dimension_name.lower() and "top" in text:
                answer_lines.append(
                    "Top customers by total revenue, ranked from highest to lowest:"
                )
            elif "product" in dimension_name.lower():
                answer_lines.append(
                    "Products by total revenue, ranked from highest to lowest:"
                )
            elif "region" in dimension_name.lower():
                answer_lines.append(
                    "Revenue by region, ranked from highest to lowest:"
                )
            else:
                answer_lines.append(
                    f"{dimension_name.title()} by total revenue, ranked from highest to lowest:"
                )
        answer_lines.append(result.head(12).to_string(index=False))
    if wants_sql and sql:
        answer_lines.append("\nSQL used:\n```sql\n" + sql + "\n```")
    pandas_code = pandas_equivalent(sql) if sql else None
    reasoning.append("DuckDB executed a read-only SELECT against in-memory tables registered from the uploaded CSVs.")
    return _pack("\n\n".join(answer_lines), reasoning, sql, chart, [], tables_used, pandas_code)


def _summary(session: Session) -> str:
    parts = ["Business snapshot from uploaded data:"]
    for name, frame in session.tables.items():
        parts.append(f"\n**{name}** â€” {len(frame)} rows Ã— {frame.shape[1]} columns.")
        revenue = _col(frame, "revenue", "sales", "amount")
        region = _col(frame, "region", "country")
        product = _col(frame, "product")
        if revenue is not None:
            parts.append(f"Total {revenue}: {frame[revenue].sum():,.2f}")
            if region:
                top = frame.groupby(region)[revenue].sum().sort_values(ascending=False).head(3)
                parts.append("Top regions: " + ", ".join(f"{idx} ({val:,.0f})" for idx, val in top.items()))
            if product:
                top_p = frame.groupby(product)[revenue].sum().sort_values(ascending=False).head(3)
                parts.append("Top products: " + ", ".join(f"{idx} ({val:,.0f})" for idx, val in top_p.items()))
    return "\n".join(parts)


def _default_chart(frame: pd.DataFrame, name: str, region: str | None, revenue: str | None, date_col: str | None):
    if date_col and revenue:
        tmp = frame.copy()
        tmp["_month"] = pd.to_datetime(tmp[date_col], errors="coerce").dt.to_period("M").astype(str)
        grouped = tmp.groupby("_month", dropna=True)[revenue].sum().reset_index()
        grouped.columns = ["month", "total_revenue"]
        return chart_from_frame(grouped, "line", f"Monthly {revenue} â€” {name}", "month", "total_revenue")
    if region and revenue:
        grouped = frame.groupby(region)[revenue].sum().reset_index().sort_values(revenue, ascending=False)
        grouped.columns = [region, "total_revenue"]
        return chart_from_frame(grouped, "bar", f"{revenue} by {region}", region, "total_revenue")
    return None


def _pack(answer, reasoning, sql, chart, anomalies, tables_used, pandas_code=None):
    if isinstance(reasoning, list):
        reasoning = " ".join(reasoning)
    return {
        "answer": answer,
        "reasoning": reasoning,
        "sql": sql,
        "pandas_code": pandas_code or (pandas_equivalent(sql) if sql else None),
        "chart": chart,
        "anomalies": anomalies,
        "tables_used": tables_used,
    }

