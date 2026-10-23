import pandas as pd

from app.local_analyst import analyze
from app.session_store import Session


def test_region_revenue_question():
    session = Session(session_id="s")
    session.tables["sales"] = pd.DataFrame(
        {
            "region": ["West", "East", "West"],
            "revenue": [100, 40, 20],
            "product": ["A", "B", "C"],
            "customer": ["Ada", "Ben", "Ada"],
            "order_date": ["2024-01-01", "2024-02-01", "2024-02-15"],
        }
    )

    result = analyze(session, "Which region generated the highest total revenue?")

    assert result["sql"]
    assert '"sales"' in result["sql"]
    assert "West" in result["answer"]
    assert "120" in result["answer"]


def test_region_revenue_selects_sales_when_customers_uploaded_first():
    session = Session(session_id="s")
    session.tables["customers"] = pd.DataFrame(
        {
            "customer": ["Ada", "Ben"],
            "region": ["West", "East"],
        }
    )
    session.tables["sales"] = pd.DataFrame(
        {
            "region": ["West", "East", "West"],
            "revenue": [100, 40, 20],
            "customer": ["Ada", "Ben", "Ada"],
        }
    )

    result = analyze(
        session,
        "Which region generated the highest total revenue? "
        "Show the revenue for each region and explain your reasoning.",
    )

    assert result["sql"]
    assert 'FROM "sales"' in result["sql"]
    assert "West" in result["answer"]
    assert "120" in result["answer"]
    assert "East" in result["answer"]


def test_monthly_sales_trend_uses_sales_and_orders_months():
    session = Session(session_id="s")
    session.tables["customers"] = pd.DataFrame(
        {
            "customer": ["Ada", "Ben"],
            "signup_date": ["2024-01-01", "2024-02-01"],
        }
    )
    session.tables["sales"] = pd.DataFrame(
        {
            "order_date": ["2024-02-10", "2024-01-15", "2024-02-20"],
            "revenue": [40, 100, 60],
        }
    )

    result = analyze(session, "Show monthly sales trends")

    assert result["sql"]
    assert 'FROM "sales"' in result["sql"]
    assert "total_revenue" in result["sql"]
    assert "2024-01" in result["answer"]
    assert "2024-02" in result["answer"]
    assert result["answer"].index("2024-01") < result["answer"].index("2024-02")
    assert "100" in result["answer"]
    assert "100.0" in result["answer"]


def test_underperforming_products_rank_lowest_revenue_first():
    session = Session(session_id="s")
    session.tables["customers"] = pd.DataFrame(
        {"customer": ["Ada", "Ben"], "segment": ["SMB", "Enterprise"]}
    )
    session.tables["sales"] = pd.DataFrame(
        {
            "product": ["Low", "High", "Medium", "Low"],
            "revenue": [10, 100, 50, 5],
        }
    )

    result = analyze(session, "Which products are underperforming?")

    assert result["sql"]
    assert 'FROM "sales"' in result["sql"]
    assert "ORDER BY total_revenue ASC" in result["sql"]
    assert "Low" in result["answer"]

