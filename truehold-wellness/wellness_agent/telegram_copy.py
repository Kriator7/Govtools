"""Public Telegram copy for TrueHold Wellness (@THWellness_bot)."""

from urllib.parse import quote

from wellness_agent.discounts import COLLEGE_HELP
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
MENU_DEEP_LINK = f"https://t.me/{REQUIRED_USERNAME}?start=menu"
BACK_DEEP_LINK = f"https://t.me/{REQUIRED_USERNAME}?start=back"
# HTML captions: https://core.telegram.org/bots/api#formatting-options
PARSE_MODE = "HTML"
# Free 🎉 party-popper effect (confetti + light sound) in private chats.
# message_effect_id: https://core.telegram.org/bots/api#sendmessage
# Free effects: https://telegram.org/blog/message-effects-and-more
CELEBRATE_EFFECT_ID = "5046509860389126442"
PAYMENT_COPY = (
    "Local Las Vegas: Zelle is best — the team shares Zelle details on the confirmation call. "
    "Prefer debit card instead of Zelle? Pay on the website."
)

INTRODUCTION = (
    "<b>Welcome to TrueHold Wellness</b>\n"
    "\n"
    "Hello — we are glad you are here. We care that you get healthy, and we'll walk with you. "
    "Official Telegram shop for Las Vegas residents. "
    "Educational research-peptide information. Dry (lyophilized) vials only.\n"
    "\n"
    "<b>How it works</b>\n"
    "1. Tap a name\n"
    "2. Sheet or Order\n"
    f"3. We call to confirm, consult, and complete required documentation\n"
    "\n"
    "Nature and God already packed the tools. Science opened the door again. We'll treat them with care.\n"
    "Prep and local delivery: Las Vegas residents only.\n"
    "Need a person? tap Team\n"
    "\n"
    f"{COLLEGE_HELP}"
)

GREET_AGAIN = (
    "<b>Hey — the floor team is here.</b>\n"
    "A new host waves each time you say hi until you have met all 21."
)

CUSTOMER_HELP = (
    f"TrueHold Wellness (@{REQUIRED_USERNAME})\n"
    "A floor host waves when you say hi, then shows the tap-menu. "
    "Each return visit introduces a new teammate until you have met all 21. "
    "Then you can rotate again or lock a favorite who always serves you.\n"
    "We care that you get healthy and feel at home in your own body, using the tools nature and God already gave us. "
    "Most peptides already exist in you — treat them with the same respect as rest and good food. Learn with us. "
    "If this house helped, you're welcome to tell others.\n"
    "Type \"lets see the crew\" (or tap 📸 Crew) for the office class photo.\n"
    "View PDF / Sheet sends the locked information sheet as a Telegram file (Files). "
    "Shop pages in Links are not the sheets.\n"
    "/menu — quick menu\n"
    "/crew — class photo of the floor team\n"
    "/schedule — talk to the TrueHold team\n"
    "/help — this message\n"
    f"{SERVICE_POLICY} Educational only. {CALL_AND_DOCS}.\n"
    f"{PAYMENT_COPY}\n"
    f"{COLLEGE_HELP}\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

STAFF_HELP = (
    f"Staff mode on @{REQUIRED_USERNAME}. Customers do not see these commands.\n"
    "/inbox — full business inbox snapshot\n"
    "/stock — on-hand inventory\n"
    "/promo — list promotion drafts (sales never auto-run)\n"
    "/promo draft Headline | body — submit for approval\n"
    "/promo approve <id> or /promo reject <id>\n"
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
    "<b>📅 Team</b>\n"
    "Phone: (702) 879-8783 · (702) 879-TRUE\n"
    f'Email: <a href="{_mailto_href()}">{TEAM_EMAIL}</a>\n'
    "Tap email to open your mail app — our address is filled in.\n"
    "\n"
    "<b>Prep</b>\n"
    "Las Vegas residents only · dry vials only\n"
    "\n"
    "<b>Pay</b>\n"
    "Zelle on the confirmation call · debit on the website\n"
    f"{COLLEGE_HELP}\n"
    f'<a href="{SHOP_URL}">trueholdwellness.com/shop</a>\n'
    "\n"
    "Protocol details are reviewed case by case. "
    "This bot does not provide dosing, reconstitution, or administration instructions in chat."
)


def schedule_keyboard(style: str | None = None, host: dict | None = None, *, back_callback: str = "w:back") -> dict:
    """Team card keyboard.

    Copy-email (copy_text) plus Debit (url) stay on this card. Back and Menu are
    https://t.me deep links, not callback_data: mixed copy_text + callback
    keyboards can leave the callback buttons inert on Telegram clients, which
    is the Team-screen lock. start payloads: https://core.telegram.org/api/links
    """
    del back_callback, host
    email = {"text": "📧 Copy email", "copy_text": {"text": TEAM_EMAIL}}
    debit = {"text": "💳 Debit", "url": SHOP_URL}
    back = {"text": "⬅️ Back", "url": BACK_DEEP_LINK}
    menu = {"text": "⬅️ Menu", "url": MENU_DEEP_LINK}
    if style in {"primary", "success", "danger"}:
        email["style"] = style
        debit["style"] = style
        back["style"] = style
        menu["style"] = style
    return {
        "inline_keyboard": [
            [email, debit],
            [back],
            [menu],
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
    {"command": "crew", "description": "Class photo of the floor team"},
    {"command": "schedule", "description": "Talk to the TrueHold team"},
    {"command": "help", "description": "How to order"},
)

STAFF_COMMANDS = CUSTOMER_COMMANDS + (
    {"command": "inbox", "description": "Staff: full business inbox snapshot"},
    {"command": "stock", "description": "Staff: on-hand inventory"},
    {"command": "promo", "description": "Staff: draft/approve sales (never auto)"},
)

# Public BotFather menu is customer-only so clients are not shown staff commands.
BOT_COMMANDS = CUSTOMER_COMMANDS
HELP = CUSTOMER_HELP
