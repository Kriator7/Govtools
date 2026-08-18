# Intake status — Home Finder Realty / Damian Einbinder

Updated from `Pirates_IG_LLC_AI_Acquisition_Criteria.numbers` (Acquisition Criteria, Property Screening, Investor Profile).

The Numbers workbook is the client source of truth. The earlier “20% of ARV” line on the criteria tab is **not** used. The Investor Profile and the screening example both confirm **10% below ARV = max purchase 90% of ARV**.

---

## Received and now built into the agent

### Realtor

- Damian Einbinder, Home Finder Realty, license B.0146854 (expires 31 July 2027)
- 9890 S Maryland Pkwy Ste 200A, 702-371-0950, binder@thehomefinderlv.com
- Buyer-side investor work only

### Pirates IG LLC

| Item | Value | Status |
| --- | --- | --- |
| Company | Pirates IG LLC | Received |
| Contact | Amos | Received |
| Phone | (310) 986-5887 | Received |
| Email | rocky12345@yahoo.com | Received |
| Active | Yes | Received |
| SMS / email OK | Not confirmed | Do not text or email Amos until Damian says Yes |
| Notes | Amos is point of contact; other investors may participate | Received |
| Property type | Single-family only | Required — in matching |
| HOA | No. Reject any HOA | Required — in matching |
| Cities | Las Vegas; North Las Vegas; Henderson | Required — in matching |
| Price | Max purchase = **90% of ARV** (10% below ARV) | Required — in matching |
| Example | $400,000 ARV → $360,000 max; 90.0% PASS | Built in as Example-001 |
| Dollar cap | None. ARV % is the only price test | Received |
| Beds / baths / sq ft / year | No minimum | Received |
| Funding | All cash, no financing contingency assumed | Stored on the profile; used when a transaction is created |
| Occupancy | TBD | Do not filter |
| Who supplies ARV | TBD | Do not invent ARV. Listings without ARV sit in `AWAITING_ARV` |

Screening columns the agent now calculates the same way as Damian’s sheet: Price ÷ ARV, Max Allowed Price, Type Pass, Area Pass, HOA Pass, Price Pass.

---

## Google sign-in error

Damian does **not** need to sign into Google for this system. The “Couldn’t sign you in / this browser or app may not be secure” page is Google blocking that browser. We do not want his Google password.

If he needs to send the workbook again:

1. In Numbers: File → Export To → Excel, then email the `.xlsx`, or
2. Email the `.numbers` file as an attachment, or
3. AirDrop / USB

Do not try to connect our bot to his Gmail or Google Drive login.

---

## Still needed (short)

1. Confirm SMS to Amos: Yes or No (currently held)
2. Confirm email to Amos: Yes or No
3. Who types ARV, and when (Damian, Amos, or an estimator)
4. Occupancy: vacant / tenant / owner / any — or leave TBD
5. Telegram username and hours he wants alerts
6. MLS name, MLS ID, and written OK to use the authorized feed (not the website)
7. Forms / e-sign platform — still not needed to screen properties

Do not re-ask name, license, cities, HOA, SFH-only, 90% ARV, Amos’s phone/email, or “any other investors” (Amos is the Pirates IG point of contact; others may join later).
