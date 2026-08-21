# Intake status — Damian packet watch is on

The Pirates IG LLC Numbers sheets remain **test templates only**. They are not live client data.

The user asked us to watch `jrupe7@gmail.com` for Damian Einbinder / Home Finder Realty replies (`binder@thehomefinderlv.com`) to the packet request and apply those replies to packet data.

`jrupe7@gmail.com` is a **separate Gmail account** from the CardanoMint SMTP login. Inbox polling uses Gmail IMAP ([IMAP/SMTP](https://developers.google.com/workspace/gmail/imap/imap-smtp)) and a Gmail App Password ([App passwords](https://support.google.com/accounts/answer/185833)). Without a `jrupe7` App Password (`IMAP_PASSWORD` / `JRUPE7_IMAP_PASSWORD`), the watcher falls back to `cardanomint@gmail.com` and still only applies mail from Damian / Home Finder — it does not scrape Zillow or other listing mail.

```
python -m app.cli inbox-poll --once
python -m app.cli inbox-poll
```

When a Damian packet reply arrives:

1. Packet 1 updates Damian Einbinder / Home Finder Realty (does not overwrite Test Operator)
2. Packets 3–4 import investor / buy-box spreadsheets onto Damian
3. Packet 5 merges Telegram / alert hours / min score
4. Packets 2 and 6–10 store metadata and files; passwords are redacted and not saved
5. A snapshot is written to gitignored `data/packets/STATUS.md`

## Packet 2 — Las Vegas REALTORS IDX (Catalino "Cat" Yee)

Recorded from the association IDX email. MLS name: Las Vegas REALTORS MLS (Matrix). Contact: Catalino "Cat" Yee, MLS Training & IDX Specialist/CALV Coordinator.

| Option | What it is | Feeds this matcher? |
| --- | --- | --- |
| 1. Matrix frame link | Free; name → settings → IDX Configuration. No agreement. | No (website iframe) |
| 2. IDX vendor API key plugin | Vendor charges. LVR waives $250 setup for a listed vendor set. https://wordpress.com/plugins/browse/idx | No (website plugin) |
| 3. Trestle WebAPI | Sign up as **technology provider** at https://trestle.corelogic.com/SubscriptionWizard. $100/month to Cotality. | Yes (authorized feed) |

Cat: **do not choose option 2 and option 3 together.** Chosen option is still empty. `MLS_PROVIDER` stays `mock`. Do not scrape Matrix. Do not sign up for Trestle until Damian or the broker picks option 3 only.

Paste apply:

```
python -m app.cli inbox-apply --from-address 'Catalino Yee <idx@lasvegasrealtors.example>' --subject 'IDX options' --body-file data/imports/packet2_las_vegas_realtors_idx.txt
```


SMS and email **relays stay on**. Do not text Damian or investors from this environment until that is explicitly enabled.

---

## Current test defaults

| Setting | Value | How to change |
| --- | --- | --- |
| Packet watch address | `jrupe7@gmail.com` | `IMAP_WATCH_ADDRESS` |
| jrupe7 IMAP login | needs App Password | `IMAP_USERNAME` + `IMAP_PASSWORD` |
| Fallback IMAP mailbox | `cardanomint@gmail.com` | `EMAIL_SMTP_USERNAME` / `EMAIL_SMTP_PASSWORD` |
| Test operator email / from address | `cardanomint@gmail.com` | `EMAIL_FROM` |
| Email relay inbox | `cardanomint@gmail.com` | `EMAIL_RELAY_TO` |
| Relay mode | on (all mail goes to the relay inbox) | `EMAIL_RELAY_MODE=true\|false` |
| Live Gmail send | off until `EMAIL_PROVIDER=smtp` + App Password | `EMAIL_SMTP_PASSWORD` |
| Telegram | live @PirateEye_bot in **MaximumMint & Agent Real** (`TELEGRAM_OPERATOR_CHAT_ID`) | `TELEGRAM_MODE=live` + `python -m app.cli telegram-poll` |
| Investor preferred channel | SMS (Damian’s stated preference) | test template only |
| SMS relay | on; live Twilio blocked without `SMS_RELAY_TO` | `SMS_RELAY_TO` = your test phone |
| Email copy of investor notices | on | `NOTIFY_EMAIL_COPY` |
| Test investor template | Pirates IG LLC rules from the Numbers workbook | seed only |
| Live realtor email | `binder@thehomefinderlv.com` | Packet 1 / `DAMIAN_EMAIL` |
| Live realtor | created when Packet 1 arrives, or from `binder@thehomefinderlv.com` mail | inbox-poll |
| Damian Telegram | `@damianlasvegas` in **MaximumMint & Agent Real**; alerts via @PirateEye_bot; buy-box notes (`$300k–$600k` buy-and-hold + stretch) | `TELEGRAM_OPERATOR_CHAT_ID` + telegram-poll |

Template matching rules (for tests, not production traffic):

- Single-family only
- No HOA
- Las Vegas / North Las Vegas / Henderson
- Max purchase = 90% of ARV
- No beds/baths/sqft/year minimums
- Missing ARV → `AWAITING_ARV` (never invent ARV)

---

## After packets are applied

Keep relays on until you explicitly turn them off:

1. Confirm Damian’s Packet 1 identity on the Damian realtor row
2. Confirm investor roster from Packets 3–4
3. Set `EMAIL_FROM` / `EMAIL_RELAY_TO` if the live from-address should change
4. Set `EMAIL_RELAY_MODE=false` only when mail should go to real investor addresses
5. Set `SMS_RELAY_MODE=false` only when texts should go to real investor phones with permission

Zillow listing emails in either inbox are **not** an MLS source. Do not scrape Gmail or Zillow for listings. Use only an authorized MLS/API feed later.

Damian wants investors contacted by **text**. That is wired as the test preferred channel, with SMS relay + an email copy. Do not send Twilio messages to Damian or his investors until that is explicitly enabled.
