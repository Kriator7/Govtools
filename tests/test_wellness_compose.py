from truehold.wellness_agent.compose import compose_alert, format_alert, format_inbox
from truehold.wellness_agent.models import REQUIRED_CATEGORIES, AlertTrigger
from truehold.wellness_agent.snapshot import load_current_inbox


REQUIRED_COPY = (
    "TrueHold Wellness order",
    "payment",
    "fulfillment request",
    "shipping issue",
    "cancellation/refund",
    "peptide message",
    "actionable business email",
    "connected inbox",
)


def test_current_inbox_includes_every_business_category():
    inbox = load_current_inbox()
    assert inbox.kind == "business_inbox_snapshot"
    assert inbox.title == "TrueHold Wellness — business inbox"
    for phrase in REQUIRED_COPY:
        assert phrase in inbox.copy
    categories = inbox.categories()
    assert tuple(categories) == REQUIRED_CATEGORIES
    for name, status in categories.items():
        assert status.new is False
        assert status.detail


def test_business_alert_is_the_inbox_snapshot():
    alert = compose_alert(AlertTrigger(type="business", headline="business inbox"))
    text = format_alert(alert)
    assert text.startswith("TrueHold Wellness — business inbox\n")
    assert "TrueHold Wellness alert —" not in text
    assert "Business:" in text
    assert "Orders:" in text
    assert "Payments:" in text
    assert "Fulfillment:" in text
    assert "Shipping:" in text
    assert "Cancellations:" in text
    assert "Peptides:" in text
    assert "Other actionable:" in text
    assert "peptide message" in text


def test_order_alert_still_includes_full_inbox_snapshot():
    alert = compose_alert(
        AlertTrigger(
            type="order",
            headline="order",
            detail="New TrueHold Wellness order received.",
        )
    )
    text = format_alert(alert)
    assert text.startswith("TrueHold Wellness alert — order")
    assert "New TrueHold Wellness order received." in text
    payload = alert.to_dict()
    assert payload["agent"] == "truehold-wellness-agent"
    for name in REQUIRED_CATEGORIES:
        assert name in payload["inbox"]
        assert "detail" in payload["inbox"][name]
        assert "new" in payload["inbox"][name]


def test_every_wellness_trigger_includes_full_snapshot():
    for trigger_type, headline in (
        ("payment", "payment"),
        ("fulfillment", "fulfillment request"),
        ("shipping", "shipping issue"),
        ("cancellation", "cancellation/refund"),
        ("peptide", "peptide message"),
        ("manual", "manual alert"),
    ):
        alert = compose_alert(AlertTrigger(type=trigger_type, headline=headline, detail="x"))
        text = format_alert(alert)
        assert "TrueHold Wellness — business inbox" in text
        assert set(alert.inbox.categories()) == set(REQUIRED_CATEGORIES)


def test_format_inbox_marks_none_when_no_new_items():
    text = format_inbox(load_current_inbox())
    assert "[none]" in text
    assert "Inbox:" in text
