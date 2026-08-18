# Intake status — testing first, Damian later

The Pirates IG LLC Numbers sheets are **test templates only**. They are not live client data.

Do not contact Damian, Amos, or Home Finder Realty from this environment until testing is confirmed.

---

## Current test defaults

| Setting | Value | How to change |
| --- | --- | --- |
| Test operator email / from address | `cardanomint@gmail.com` | `EMAIL_FROM` |
| Email relay inbox | `cardanomint@gmail.com` | `EMAIL_RELAY_TO` |
| Relay mode | on (all mail goes to the relay inbox) | `EMAIL_RELAY_MODE=true\|false` |
| Test investor template | Pirates IG LLC rules from the Numbers workbook | seed only |
| Live realtor | not loaded | add Damian after testing |

Template matching rules (for tests, not production traffic):

- Single-family only
- No HOA
- Las Vegas / North Las Vegas / Henderson
- Max purchase = 90% of ARV
- No beds/baths/sqft/year minimums
- Missing ARV → `AWAITING_ARV` (never invent ARV)

---

## After testing confirms the pipeline

Then collect Damian’s live packet (identity already on file from his first reply) and switch:

1. Seed Damian Einbinder / Home Finder Realty as the active realtor
2. Replace the test investor with his real roster and permissions
3. Set `EMAIL_FROM` / `EMAIL_RELAY_TO` if the live from-address should change
4. Set `EMAIL_RELAY_MODE=false` only when mail should go to real investor addresses

Until then, outbound email is from and to `cardanomint@gmail.com`.

The operator mailbox is confirmed as the CardanoMint Gmail account (`cardanomint@gmail.com`). Mock email still writes `data/exports/email_outbox.json`; live Gmail SMTP/OAuth is not wired yet.

Zillow listing emails in that inbox are **not** an MLS source. Do not scrape Gmail or Zillow for listings. Use only an authorized MLS/API feed later.
