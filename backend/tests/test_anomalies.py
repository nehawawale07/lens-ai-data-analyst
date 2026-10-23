import pandas as pd

from app.anomaly_service import detect_anomalies


def test_flags_extreme_value():
    frame = pd.DataFrame({"revenue": [10, 11, 9, 10, 12, 11, 10, 9, 1000]})
    findings = detect_anomalies(frame, "sales")
    flagged = [item for item in findings if item.get("count")]
    assert flagged
    assert flagged[0]["column"] == "revenue"
