import pandas as pd

from app.session_store import Session
from app.sql_service import SqlError, execute_sql


def _session() -> Session:
    session = Session(session_id="test")
    session.tables["sales"] = pd.DataFrame({"region": ["West", "East"], "revenue": [10, 25]})
    return session


def test_select_works():
    result = execute_sql(_session(), "SELECT region, SUM(revenue) AS total FROM sales GROUP BY 1")
    assert set(result["region"]) == {"West", "East"}


def test_rejects_writes():
    try:
        execute_sql(_session(), "DELETE FROM sales")
        assert False
    except SqlError:
        pass
