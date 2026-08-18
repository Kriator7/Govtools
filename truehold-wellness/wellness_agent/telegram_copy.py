"""Public Telegram copy for TrueHold Wellness (@THWellness_bot)."""

from wellness_agent.identity import REQUIRED_USERNAME

CUSTOMER_HELP = (
    f"TrueHold Wellness (@{REQUIRED_USERNAME})\n"
    "Scroll the pictures and tap This one on the vial you want.\n"
    "/menu — picture menu\n"
    "/schedule — talk to the TrueHold team\n"
    "/help — this message\n"
    "Las Vegas residents only. Educational only. The team confirms before payment.\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

STAFF_HELP = (
    f"Staff mode on @{REQUIRED_USERNAME}. Customers do not see these commands.\n"
    "/inbox — full business inbox snapshot\n"
    "/menu — same picture menu customers use\n"
    "Order and email-reflex alerts arrive in this chat.\n"
    "This bot is not realtor-agent / @PirateEye_bot."
)

SCHEDULE = (
    "TrueHold Wellness — book with the team\n"
    "Phone: (702) 879-8783 or (702) 879-TRUE\n"
    "Email: TRUEHOLDWELLNESS@GMAIL.COM\n"
    "Shop: https://trueholdwellness.com/shop\n"
    "Las Vegas residents only for Telegram interest orders.\n"
    "Protocol details are reviewed case by case. "
    "This bot does not provide dosing, reconstitution, or administration instructions in chat."
)

CUSTOMER_COMMANDS = (
    {"command": "start", "description": "Picture menu — tap the vial you want"},
    {"command": "menu", "description": "Show the picture menu"},
    {"command": "schedule", "description": "Talk to the TrueHold team"},
    {"command": "help", "description": "How to order"},
)

STAFF_COMMANDS = CUSTOMER_COMMANDS + (
    {"command": "inbox", "description": "Staff: full business inbox snapshot"},
)

# Public BotFather menu is customer-only so clients are not shown staff commands.
BOT_COMMANDS = CUSTOMER_COMMANDS
HELP = CUSTOMER_HELP
