import json
from datetime import datetime, timezone

from mr_north.bls import BlsSnapshot, SeriesPrint, fetch_snapshot, format_breakdown


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _payload() -> dict:
    return {
        "status": "REQUEST_SUCCEEDED",
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": "LNS14000000",
                    "data": [
                        {"year": "2026", "period": "M07", "periodName": "July", "value": "4.1"},
                        {"year": "2026", "period": "M06", "periodName": "June", "value": "4.2"},
                        {"year": "2025", "period": "M07", "periodName": "July", "value": "4.2"},
                    ],
                },
                {
                    "seriesID": "CES0000000001",
                    "data": [
                        {"year": "2026", "period": "M07", "periodName": "July", "value": "158858"},
                        {"year": "2026", "period": "M06", "periodName": "June", "value": "158881"},
                    ],
                },
                {
                    "seriesID": "CES0500000003",
                    "data": [
                        {"year": "2026", "period": "M07", "periodName": "July", "value": "37.62"},
                        {"year": "2026", "period": "M06", "periodName": "June", "value": "37.60"},
                    ],
                },
                {
                    "seriesID": "CUUR0000SA0",
                    "data": [
                        {"year": "2026", "period": "M07", "periodName": "July", "value": "333.918"},
                        {"year": "2026", "period": "M06", "periodName": "June", "value": "333.952"},
                        {"year": "2025", "period": "M07", "periodName": "July", "value": "322.132"},
                    ],
                },
                {
                    "seriesID": "CUUR0000SA0L1E",
                    "data": [
                        {"year": "2026", "period": "M07", "periodName": "July", "value": "340.0"},
                        {"year": "2026", "period": "M06", "periodName": "June", "value": "339.0"},
                    ],
                },
            ]
        },
    }


def test_fetch_snapshot_builds_official_prints():
    captured = {}

    def opener(request, timeout=30):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(_payload())

    snapshot = fetch_snapshot(opener=opener)
    assert captured["url"] == "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    assert "LNS14000000" in captured["body"]["seriesid"]
    by_id = {row.series_id: row for row in snapshot.prints}
    assert by_id["LNS14000000"].value == 4.1
    text = format_breakdown(snapshot)
    assert text.startswith("Mr North hourly — Bureau of Labor Statistics")
    assert "Unemployment rate" in text
    assert "4.1%" in text
    assert "Total nonfarm payrolls" in text
    assert "CPI-U all items" in text
    assert "www.bls.gov/developers/api_signature.htm" in text
    assert "peptide" not in text.lower()


def test_format_breakdown_marks_unchanged_hour():
    snapshot = BlsSnapshot(
        fetched_at=datetime(2026, 8, 20, 16, 0, tzinfo=timezone.utc),
        prints=(
            SeriesPrint(
                series_id="LNS14000000",
                label="Unemployment rate (SA)",
                unit="percent",
                year="2026",
                period="M07",
                period_name="July",
                value=4.1,
                previous_value=4.2,
                yoy_value=4.2,
            ),
        ),
        fingerprint="x",
    )
    text = format_breakdown(snapshot, unchanged=True)
    assert "No new BLS print this hour" in text
