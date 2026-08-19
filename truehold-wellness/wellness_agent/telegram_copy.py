"""Public Telegram copy for TrueHold Wellness (@THWellness_bot)."""

from urllib.parse import quote

from wellness_agent.identity import REQUIRED_USERNAME

SAY_HI = (
    "Welcome to TrueHold Wellness.\n"
    "\n"
    "Send /start, or just say hello, and we will show you how ordering works."
)

CALL_AND_DOCS = (
    "The team calls to confirm, consult, and complete required documentation"
)

SERVICE_POLICY = (
    "Prep and local delivery are for Las Vegas residents only. "
    "We ship dry (lyophilized) vials only — not reconstituted product."
)

SHOP_URL = "https://trueholdwellness.com/shop"
PAYMENT_COPY = (
    "Local Las Vegas: Zelle is best — the team shares Zelle details on the confirmation call. "
    "Prefer debit card instead of Zelle? Pay on the website."
)

INTRODUCTION = (
    "Welcome to TrueHold Wellness.\n"
    "\n"
    "Hello — we are glad you are here. This is the official TrueHold Wellness "
    "Telegram shop. We help Las Vegas residents with educational research-peptide "
    "information and take interest orders for dry (lyophilized) vials only.\n"
    "\n"
    "How it works:\n"
    "1. Tap a name below. We send that one product tile — not the whole catalog.\n"
    "2. View PDF in Telegram, or Order this for 1, 2, or 3 dry vials.\n"
    "3. Confirm you are a Las Vegas resident. We log the order, adjust inventory, "
    f"and {CALL_AND_DOCS.lower()} before any payment.\n"
    "\n"
    f"{SERVICE_POLICY}\n"
    "Need a person instead? /schedule"
)

GREET_AGAIN = (
    "Hi again. Send /menu for the quick list, or tap a name already on screen."
)

CUSTOMER_HELP = (
    f"TrueHold Wellness (@{REQUIRED_USERNAME})\n"
    "Send /start for a welcome, then tap one name — we send that tile, not the whole list.\n"
    "/menu — quick menu\n"
    "/schedule — talk to the TrueHold team\n"
    "/help — this message\n"
    f"{SERVICE_POLICY} Educational only. {CALL_AND_DOCS}.\n"
    f"{PAYMENT_COPY}\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

STAFF_HELP = (
    f"Staff mode on @{REQUIRED_USERNAME}. Customers do not see these commands.\n"
    "/inbox — full business inbox snapshot\n"
    "/stock — on-hand inventory\n"
    "/menu — same picture menu customers use\n"
    "Order and email-reflex alerts arrive in this chat.\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

TEAM_EMAIL = "trueholdwellness@gmail.com"
EMAIL_SUBJECT = "Question for TrueHold Wellness"
EMAIL_BODY = "Hi TrueHold team,\n\nI have a question:\n\n"
# mailto opens the client's own mail app with To/subject/body filled.
# Telegram URL buttons only allow http/https, so this lives in the message as HTML.
# https://core.telegram.org/bots/api#formatting-options
MAILTO_URL = (
    f"mailto:{TEAM_EMAIL}"
    f"?subject={quote(EMAIL_SUBJECT)}"
    f"&body={quote(EMAIL_BODY)}"
)
SCHEDULE_PARSE_MODE = "HTML"


def _mailto_href() -> str:
    return MAILTO_URL.replace("&", "&amp;")


SCHEDULE = (
    "TrueHold Wellness — book with the team\n"
    "Phone: (702) 879-8783 or (702) 879-TRUE\n"
    f'Email: <a href="{_mailto_href()}">{TEAM_EMAIL}</a>\n'
    "Tap the email to open your mail app. Our address is already filled in — "
    "type your question and send.\n"
    f"{SERVICE_POLICY}\n"
    f"{PAYMENT_COPY}\n"
    f'Debit-card checkout: <a href="{SHOP_URL}">{SHOP_URL}</a>\n'
    "Telegram interest orders are for Las Vegas residents only.\n"
    "Protocol details are reviewed case by case. "
    "This bot does not provide dosing, reconstitution, or administration instructions in chat."
)


def schedule_keyboard() -> dict:
    """copy_text: https://core.telegram.org/bots/api#copytextbutton"""
    return {
        "inline_keyboard": [
            [{"text": "Copy email address", "copy_text": {"text": TEAM_EMAIL}}],
            [{"text": "Pay by debit card on the site", "url": SHOP_URL}],
        ]
    }


def send_schedule(telegram, chat_id: str) -> None:
    try:
        telegram.send_message(
            chat_id,
            SCHEDULE,
            reply_markup=schedule_keyboard(),
            parse_mode=SCHEDULE_PARSE_MODE,
        )
    except TypeError:
        telegram.send_message(chat_id, SCHEDULE, reply_markup=schedule_keyboard())

CUSTOMER_COMMANDS = (
    {"command": "start", "description": "Welcome to TrueHold Wellness"},
    {"command": "menu", "description": "Quick menu — tap one name"},
    {"command": "schedule", "description": "Talk to the TrueHold team"},
    {"command": "help", "description": "How to order"},
)

STAFF_COMMANDS = CUSTOMER_COMMANDS + (
    {"command": "inbox", "description": "Staff: full business inbox snapshot"},
    {"command": "stock", "description": "Staff: on-hand inventory"},
)

# Public BotFather menu is customer-only so clients are not shown staff commands.
BOT_COMMANDS = CUSTOMER_COMMANDS
HELP = CUSTOMER_HELP
