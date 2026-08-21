"""Las Vegas REALTORS® IDX options from Catalino Yee (Packet 2).

Source email: Catalino "Cat" Yee, MLS Training & IDX Specialist/CALV Coordinator,
Las Vegas REALTORS. Do not scrape Matrix. Do not invent Trestle/RESO payloads.
Trestle signup: https://trestle.corelogic.com/SubscriptionWizard
"""

from __future__ import annotations

TRESTLE_SIGNUP_URL = "https://trestle.corelogic.com/SubscriptionWizard"
WORDPRESS_IDX_PLUGIN_LIST = "https://wordpress.com/plugins/browse/idx"

LAS_VEGAS_REALTORS_MLS = "Las Vegas REALTORS MLS (Matrix)"
IDX_CONTACT_NAME = 'Catalino "Cat" Yee'
IDX_CONTACT_ROLE = "MLS Training & IDX Specialist/CALV Coordinator"
IDX_CONTACT_ORG = "Las Vegas REALTORS"

# Cat: vendors Las Vegas REALTORS does not charge the $250 setup fee.
NO_LVR_SETUP_FEE_VENDORS = (
    "Perfect Storm",
    "Placester.Com",
    "Moxiworks",
    "Bold Street",
    "Real Scout",
    "Terradatum",
    "Follow Up Boss/Zillow",
    "Inside Real Estate/Amp Stats",
    "Home Junction",
    "Proagent Websites",
    "Sierra Interactive",
    "Brokermint",
    "Clearcapital.Com Inc",
    "Constellation Web Solutions",
    "List Reports",
    "Relitix",
    "Home Asap",
    "Ihomefinder",
    "Agent Personal Assist.",
    "Idx.Inc/Elm Street Technologies",
    "Property Hook Up",
    "Anywhere Real Estate",
)

IDX_OPTIONS = {
    "1": {
        "name": "Matrix frame link",
        "cost": "free",
        "agreement_required": False,
        "how": (
            "In Matrix, click your name, click settings, and go into IDX Configuration "
            "to create your frame link."
        ),
        "feeds_this_agent": False,
        "notes": "Website iframe only. Not a listing API for match/score.",
    },
    "2": {
        "name": "API Key plugin from an IDX vendor",
        "cost": "vendor charges; Las Vegas REALTORS waives $250 setup fee for listed vendors",
        "agreement_required": True,
        "how": (
            "Obtain an API key plugin from an IDX vendor (iHomefinder, Placester, "
            "Proagent websites, Constellation Web Solutions, ListReports, Inside Real Estate, "
            f"Broker IDX/Elm Street Technologies, or others). Vendor list: {WORDPRESS_IDX_PLUGIN_LIST}"
        ),
        "feeds_this_agent": False,
        "no_lvr_setup_fee_vendors": list(NO_LVR_SETUP_FEE_VENDORS),
        "notes": "Website IDX plugins. Cat: do not choose option 2 and option 3 together.",
    },
    "3": {
        "name": "Trestle WebAPI data feed",
        "cost": "$100 monthly to Cotality",
        "agreement_required": True,
        "how": (
            f"Sign up as a technology provider at {TRESTLE_SIGNUP_URL}. "
            "Trestle: technology providers connect to data providers; broker feeds are for "
            "internal broker system use. If a broker requests a feed for a technology provider, "
            "the technology provider must subscribe."
        ),
        "feeds_this_agent": True,
        "notes": (
            "Authorized RESO/Web API path for this matcher. Do not implement a Trestle client "
            "or store credentials until Damian/broker chooses option 3 only and supplies access. "
            "Do not combine with option 2."
        ),
    },
}

PACKET_2_FROM_CAT = {
    "mls_name": LAS_VEGAS_REALTORS_MLS,
    "idx_contact_name": IDX_CONTACT_NAME,
    "idx_contact_role": IDX_CONTACT_ROLE,
    "idx_contact_org": IDX_CONTACT_ORG,
    "idx_option_1": IDX_OPTIONS["1"]["name"],
    "idx_option_2": IDX_OPTIONS["2"]["name"],
    "idx_option_3": IDX_OPTIONS["3"]["name"],
    "idx_rule": "Do NOT choose option 2 and option 3 together",
    "chosen_idx_option": "",
    "agent_usable_option": "3",
    "trestle_signup_url": TRESTLE_SIGNUP_URL,
    "api_vendor": "Trestle (Cotality) if option 3 is chosen later",
}


def looks_like_las_vegas_realtors_idx(text: str) -> bool:
    lowered = (text or "").lower()
    return (
        "idx" in lowered
        and ("trestle" in lowered or "matrix" in lowered)
        and ("catalino" in lowered or "las vegas realtor" in lowered or "cotality" in lowered)
    )
