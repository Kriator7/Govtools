from mr_north.catalyst import load_current_catalyst
from mr_north.compose import compose_alert, format_alert, format_catalyst
from mr_north.models import AlertTrigger


REQUIRED_PHRASES = (
    "Strait of Hormuz",
    "Donald Trump",
    "Reuters",
    "one-fifth of global oil supply",
    "29% above year-ago",
    "$63K",
    "$65K",
    "Macro Liquidity",
)


def _briefing_blob(briefing) -> str:
    return " ".join(
        [
            briefing.title,
            briefing.summary,
            briefing.why_it_matters,
            briefing.crypto,
            briefing.watch_next,
        ]
    )


def test_current_catalyst_loads_required_fields():
    briefing = load_current_catalyst()
    assert briefing.kind == "geopolitical_market_catalyst"
    assert briefing.title == "Alert — geopolitical / market catalyst"
    blob = _briefing_blob(briefing)
    for phrase in REQUIRED_PHRASES:
        assert phrase in blob, f"missing {phrase!r}"


def test_geopolitical_alert_is_the_catalyst_briefing():
    alert = compose_alert(
        AlertTrigger(type="geopolitical_catalyst", headline="geopolitical / market catalyst")
    )
    text = format_alert(alert)
    assert text.startswith("Alert — geopolitical / market catalyst\n")
    assert "Mr North alert —" not in text
    assert "---" not in text
    for phrase in REQUIRED_PHRASES:
        assert phrase in text


def test_btc_threshold_alert_also_includes_catalyst_data():
    alert = compose_alert(
        AlertTrigger(
            type="btc_threshold",
            headline="BTC threshold",
            detail="BTC crossed the $65K watch level.",
        )
    )
    text = format_alert(alert)
    assert text.startswith("Mr North alert — BTC threshold")
    assert "BTC crossed the $65K watch level." in text
    assert "Alert — geopolitical / market catalyst" in text
    assert "Strait of Hormuz" in text
    assert alert.catalyst.kind == "geopolitical_market_catalyst"
    payload = alert.to_dict()
    assert payload["agent"] == "mr-north"
    assert payload["catalyst"]["watch_next"].startswith("oil is now particularly important")
    assert "business" not in payload["catalyst"]


def test_every_crypto_trigger_type_attaches_catalyst():
    for trigger_type, headline in (
        ("capital_regime", "capital-regime transition"),
        ("macro_liquidity", "Macro Liquidity"),
        ("manual", "manual alert"),
    ):
        alert = compose_alert(AlertTrigger(type=trigger_type, headline=headline))
        text = format_alert(alert)
        assert "Alert — geopolitical / market catalyst" in text
        assert alert.catalyst.summary.startswith("A material macro catalyst")


def test_format_catalyst_uses_money_flow_label():
    text = format_catalyst(load_current_catalyst())
    assert "Why this matters to our money-flow watch:" in text
    assert "Crypto:" in text
    assert "Watch next:" in text
    assert "Business:" not in text
