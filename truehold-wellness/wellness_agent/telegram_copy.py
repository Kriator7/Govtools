"""Public Telegram copy for TrueHold Wellness (@THWellness_bot)."""

from wellness_agent.identity import REQUIRED_USERNAME

SAY_HI = (
    "Welcome to TrueHold Wellness.\n"
    "\n"
    "Say hi to start the conversation.\n"
    "Hello, hey, or good morning all work."
)

CALL_AND_DOCS = (
    "The team calls to confirm, consult, and complete required documentation"
)

SERVICE_POLICY = (
    "Prep and local delivery are for Las Vegas residents only. "
    "We ship dry (lyophilized) vials only — not reconstituted product."
)

INTRODUCTION = (
    "Hi — welcome to TrueHold Wellness.\n"
    "\n"
    "We help Las Vegas residents with educational research-peptide information.\n"
    f"{SERVICE_POLICY}\n"
    f"{CALL_AND_DOCS} before any payment.\n"
    "\n"
    "Tap one name on the quick menu. We will send that tile.\n"
    "Need a person instead? /schedule"
)

GREET_AGAIN = (
    "Hi again. Send /menu for the quick list, or tap a name already on screen."
)

CUSTOMER_HELP = (
    f"TrueHold Wellness (@{REQUIRED_USERNAME})\n"
    "Say hi to start. Then tap one name — we send that tile, not the whole list.\n"
    "/menu — quick menu\n"
    "/schedule — talk to the TrueHold team\n"
    "/help — this message\n"
    f"{SERVICE_POLICY} Educational only. {CALL_AND_DOCS}.\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

STAFF_HELP = (
    f"Staff mode on @{REQUIRED_USERNAME}. Customers do not see these commands.\n"
    "/inbox — full business inbox snapshot\n"
    "/menu — same picture menu customers use\n"
    "Order and email-reflex alerts arrive in this chat.\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

TEAM_EMAIL = "trueholdwellness@gmail.com"
# HTTPS Gmail compose — Telegram URL buttons require http/https, not mailto.
# https://core.telegram.org/bots/api#inlinekeyboardbutton
GMAIL_COMPOSE_URL = (
    "https://mail.google.com/mail/?view=cm&fs=1&to=trueholdwellness@gmail.com"
)

SCHEDULE = (
    "TrueHold Wellness — book with the team\n"
    "Phone: (702) 879-8783 or (702) 879-TRUE\n"
    "Email: trueholdwellness at gmail.com\n"
    "Tap Email on Gmail below to write us.\n"
    "Shop: https://trueholdwellness.com/shop\n"
    f"{SERVICE_POLICY}\n"
    "Telegram interest orders are for Las Vegas residents only.\n"
    "Protocol details are reviewed case by case. "
    "This bot does not provide dosing, reconstitution, or administration instructions in chat."
)


def schedule_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "Email on Gmail", "url": GMAIL_COMPOSE_URL}],
        ]
    }

CUSTOMER_COMMANDS = (
    {"command": "start", "description": "Say hi to start"},
    {"command": "menu", "description": "Quick menu — tap one name"},
    {"command": "schedule", "description": "Talk to the TrueHold team"},
    {"command": "help", "description": "How to order"},
)

STAFF_COMMANDS = CUSTOMER_COMMANDS + (
    {"command": "inbox", "description": "Staff: full business inbox snapshot"},
)

# Public BotFather menu is customer-only so clients are not shown staff commands.
BOT_COMMANDS = CUSTOMER_COMMANDS
HELP = CUSTOMER_HELP
