from app.csv_service import CsvValidationError, load_csv, sanitize_table_name


def test_sanitize_and_dedupe_names():
    existing = {"sales"}
    assert sanitize_table_name("Sales.csv", existing) == "sales_2"
    assert sanitize_table_name("123 data.csv", set()) == "table_123_data"


def test_rejects_empty_and_non_csv():
    try:
        load_csv(b"", "file.csv", 1000)
        assert False
    except CsvValidationError:
        pass
    try:
        load_csv(b"a,b\n1,2", "notes.txt", 1000)
        assert False
    except CsvValidationError:
        pass


def test_parses_valid_csv():
    frame, warnings = load_csv(b"region,revenue\nWest,10\nEast,20\n", "sales.csv", 10_000)
    assert list(frame.columns) == ["region", "revenue"]
    assert len(frame) == 2
    assert warnings == []
