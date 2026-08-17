# Realtor document collection checklist

Give this list to the realtor. Ask them to send one folder (Google Drive, Dropbox, or email zip) named with today’s date.

Do **not** put MLS passwords, Telegram bot tokens, Twilio keys, or e-sign passwords in email. For those, use a phone call or a password manager share after the rest of the packet arrives.

Mark each item: **Ready** / **Don’t have** / **Need permission first**.

---

## Packet 1 — Who you are (required)

Send a one-page sheet or scan:

1. Full legal name as it appears on your Nevada real-estate license
2. Brokerage legal name and DBA (if any)
3. Nevada license number and expiration date
4. Broker / designated broker name and license number
5. Office address, city, ZIP
6. Mobile phone you want used for alerts
7. Work email
8. Timezone you work in (Nevada is usually Pacific)
9. Whether you are the listing-side, buyer-side, or both for these investor deals

---

## Packet 2 — MLS / listing access (required for live listings)

We will only use access the realtor or brokerage is authorized to give. We will not scrape the MLS website.

Please send:

1. MLS name (for example: Greater Las Vegas Association of REALTORS® MLS / GLVAR, or whatever you actually use)
2. Your MLS agent ID
3. Written confirmation from you or the broker that we may use the **authorized API or data feed**, not the public website
4. The vendor name of that feed, if you know it (Bridge, Spark, RESO Web API, broker-provided export, etc.)
5. Any vendor welcome email, API docs PDF, or broker IT instructions
6. Coverage area we should watch (counties / cities). Default assumption: Clark County — Las Vegas, Henderson, North Las Vegas, plus any others you name
7. Which listing statuses to watch: Active only, or also Coming Soon / Back on Market / Price Reduced
8. Whether we may store listing remarks and agent remarks
9. Whether we may store listing photos and the MLS listing URL
10. How often you want new listings checked (example: every 15 minutes during business hours)

If the broker must request the API, send the broker’s contact and say so. We can wait. Do not invent access.

---

## Packet 3 — Investor list (required)

Send the current investor clientele as **Excel or CSV**. Google Sheets: use File → Download → Excel or CSV.

One row per investor, or one row per investor *buy box* if they have more than one.

Minimum columns:

| Column | Example | Required? |
| --- | --- | --- |
| Investor Name | ABC Capital | Yes |
| Contact Name | Jane Doe | Yes |
| Phone | +1 702 555 0100 | Yes, if you want SMS |
| Email | jane@abccapital.com | Yes, if you want email later |
| Preferred Channel | SMS | Yes |
| May we text them? | Yes / No | Yes |
| May we email them? | Yes / No | Yes |
| Active? | Yes / No | Yes |
| Assigned notes | Cash buyer, replies fast | Optional |

Do not send Social Security numbers, bank logins, or wire instructions.

---

## Packet 4 — Investor buy boxes / criteria (required)

For **each** investor, send one or more acquisition profiles. An investor can have more than one (example: Las Vegas rentals **and** Henderson multifamily).

For each profile, fill in what you can. Write **Must have** or **Nice to have** next to each rule.

| Field | Example | Must / Nice |
| --- | --- | --- |
| Profile name | Las Vegas single-family rentals | — |
| Minimum price | 200000 | |
| Maximum price | 450000 | |
| Cities | Las Vegas, Henderson | |
| ZIP codes | 89123, 89119, 89120 | |
| Neighborhoods | Silverado Ranch, Anthem | |
| Property types | Single family / Multifamily / Condo / Townhouse / Land | |
| Min bedrooms | 3 | |
| Min bathrooms | 2 | |
| Min sq ft | 1500 | |
| Min lot size | 5000 | |
| Year built min / max | 1990+ | |
| HOA allowed? | No / Yes, max $250/mo | |
| Max days on market | 30 | |
| Price reduction required? | Yes / No | |
| Occupancy | Vacant / Tenant / Owner / Any | |
| Min estimated rent | 2200 | |
| Min cap rate | 6% | |
| Max GRM | 15 | |
| Max repair budget | 25000 | |
| Cash-flow need | 300/mo | |
| Max purchase price | 450000 | |
| Desired discount | 10% below ask | |
| Desired equity | 40000 | |
| Seller financing wanted? | Yes / No | |
| Foreclosure / short sale / assumable loan wanted? | Yes / No | |
| Areas or property types to **exclude** | No 89101, no HOA condos | |
| Cash or finance | Cash | |
| Notes | Prefers 1990+; will look at 1980s | |

If they only have this in their head, a voice note or email per investor is fine. We will turn it into the table and send it back for approval before it goes live.

---

## Packet 5 — How you want to be alerted (required for live alerts)

1. Confirm you will use **Telegram** as the command center (Approve / Reject / Snooze / Details)
2. The mobile number that will install Telegram
3. After you create a Telegram account, send us the username (example: `@name`)
4. We will send you a bot-join instruction later. Do **not** create API keys yourself unless we ask
5. Hours we may alert you (example: 7:00 a.m. – 8:00 p.m. Pacific, seven days)
6. Minimum match score to alert you: 90 only, 80+, or 70+
7. Whether to re-alert on price drops and “back on market”

---

## Packet 6 — How investors get notified (required before investor texts)

1. Written OK that you want us to text investors **only after you tap Approve**
2. Your Twilio account, **or** say “I do not have Twilio — please set it up”
3. The outbound phone number investors will see (must be a number you control)
4. A short sample text you already send investors, if you have one
5. The exact reply words you want: YES / NO / MORE INFO is the default
6. Whether any investor must be called instead of texted
7. Proof each investor has agreed to receive property texts from you (TCPA). A note on the investor sheet is enough if that is how you already work

Do not email the Twilio password. Share it separately.

---

## Packet 7 — Forms we are allowed to use (required before live documents)

We **cannot** copy Nevada REALTORS®, MLS, brokerage, or title-company forms unless you confirm we are allowed to store, fill, send, and e-sign them.

For each form you actually use, send the file **and** answer the five questions under it.

Send these if you use them:

1. Residential purchase agreement (the exact version you use in Nevada)
2. Any counteroffer form
3. Common addenda you use (as-is, inspection, appraisal, HOA, lead-based paint, etc.)
4. Required Nevada disclosures you attach to investor offers
5. Brokerage-specific forms
6. HOA / association resale or demand forms, if you handle those
7. Financing / proof-of-funds request you send investors
8. Any investor-only intake or term sheet you already use

For **each** file, write on a cover sheet:

1. Official form name and version / revision date
2. Who owns it (Nevada REALTORS®, your broker, title company, you created it, other)
3. May we **store** a blank copy in the system? Yes / No
4. May we **fill it electronically**? Yes / No
5. May we **send it** to the investor or the other agent? Yes / No
6. May it be **e-signed**? Yes / No
7. Is it a fillable PDF already? Yes / No
8. Where do you normally complete it today? (Dotloop, Qualia, skySlope, DocuSign, paper, other)

If the answer is “I am not sure we can copy that form,” say so. We will use your existing transaction platform instead of storing a bootleg copy.

---

## Packet 8 — Transaction / e-sign platform (required before live offers)

1. Platform name you already use (Dotloop, skySlope, Qualia, Brokermint, DocuSign, HelloSign, other)
2. Whether the **broker** requires that platform
3. Your login username only (not the password)
4. Any API, Zapier, or “integration” page the vendor gave the office
5. Who must sign: buyer, you, broker, listing agent
6. Who is allowed to press Send on an offer — you only, or broker review first
7. A screenshot of one **closed** file’s document list (blur addresses if needed) so we can match the real checklist

---

## Packet 9 — Two or three sample closed investor deals (strongly recommended)

For each sample, send what you are allowed to share. Black out SSNs, account numbers, and birth dates.

1. The listing printout or MLS sheet as you first saw it
2. Why you sent it to that investor (even three bullet points)
3. The text or email you sent the investor
4. Their reply
5. The filled purchase agreement (executed copy)
6. Final purchase price, earnest money, closing date, financing type
7. Your commission amount, if you want later reporting

These samples let us map fields correctly and match your real wording.

---

## Packet 10 — Office rules (short answers)

1. Default earnest money you use if the investor does not specify
2. Default inspection / due-diligence days
3. Default closing timeline (example: 14 days cash, 30 days financed)
4. Who the buyer name should be on contracts (entity vs person) — or “ask every time”
5. Any city, ZIP, or HOA you never want alerted
6. After-hours: queue alerts until morning, or send immediately
7. Who we contact if the system is down (you, an assistant, the broker)

---

## What we do **not** need

- Social Security numbers
- Bank account or wire packets
- Investor tax returns
- MLS website passwords sent by email
- Permission to scrape the MLS
- Legal opinions from us — you and the broker remain the license holders

---

## Suggested send order

Send Packets **1, 3, 4, and 5** first. That is enough to import investors and start match alerts.

Send Packets **2 and 6** next so live listings and investor texts can replace the mocks.

Send Packets **7, 8, and 9** before any real document is generated.

If something is missing, write “Don’t have” rather than skipping the line. We will not guess form language, prices, or MLS access.
