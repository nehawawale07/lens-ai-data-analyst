import pandas as pd

from app.kpi_service import build_dataset_kpis, build_session_kpis


def test_dataset_kpis_count_rows_columns_missing_and_duplicates():
    frame = pd.DataFrame({
        "amount": [1, 2, None, 2],
        "category": ["a", "b", "c", "b"],
    })

    result = build_dataset_kpis("sales", frame)

    assert result["rows"] == 4
    assert result["columns"] == 2
    assert result["missing_cells"] == 1
    assert result["duplicate_rows"] == 1
    assert result["missing_percentage"] == 12.5


def test_dataset_kpis_summarize_numeric_columns():
    frame = pd.DataFrame({"amount": [1, 2, None, 2]})

    result = build_dataset_kpis("sales", frame)

    summary = result["numeric_summary"][0]
    assert summary["column"] == "amount"
    assert summary["count"] == 3
    assert summary["sum"] == 5
    assert abs(summary["mean"] - (5 / 3)) < 1e-9


def test_session_kpis_aggregate_multiple_datasets():
    tables = {
        "sales": pd.DataFrame({"amount": [10, 20]}),
        "customers": pd.DataFrame({"age": [25, 30], "city": ["Pune", "Mumbai"]}),
    }

    result = build_session_kpis(tables)

    assert result["dataset_count"] == 2
    assert result["total_rows"] == 4
    assert result["total_columns"] == 3
    assert len(result["datasets"]) == 2


def test_session_kpis_handle_empty_session():
    result = build_session_kpis({})

    assert result["dataset_count"] == 0
    assert result["total_rows"] == 0
    assert result["total_columns"] == 0
    assert result["total_missing_cells"] == 0
    assert result["datasets"] == []
