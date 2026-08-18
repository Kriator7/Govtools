# Intake status — Home Finder Realty / Damian Einbinder

Updated after the second Pirates IG LLC criteria screenshot (cities added).

Do not re-ask for items marked **Received**. Ask only for **Still needed**.

---

## Received

### Realtor

| Item | Value |
| --- | --- |
| Name | Damian Einbinder |
| Brokerage | Home Finder Realty |
| Nevada license | B.0146854, expires 31 July 2027 |
| Broker on file | Damian Einbinder, B.0146854 (same person — confirm he is the designated broker) |
| Office | 9890 S Maryland Pkwy, Ste 200A |
| Mobile | 702-371-0950 |
| Email | binder@thehomefinderlv.com |
| Role for this system | Buyer-side investor deals only |

Office city/ZIP still unstated (Las Vegas implied). Timezone: assume America/Los_Angeles unless he says otherwise.

### Pirates IG LLC — Acquisition Criteria tab (strict)

Source: `Pirates_IG_LLC_AI_Acquisition_Criteria`, tab **Acquisition Criteria**.

| Rule | Field | Operator | Value | Priority |
| --- | --- | --- | --- | --- |
| PIG-001 | Property type | Equals | Single-family home | Required |
| PIG-002 | HOA | Equals | No | Required |
| PIG-003 | Purchase price / ARV | ≤ | 20% | Required |
| PIG-004 | City | In list | Las Vegas; North Las Vegas; Henderson | Required |

Combined rule on the sheet: *“A property qualifies only if it is a single-family home in Las Vegas, North Las Vegas, or Henderson, has no HOA, and can be purchased for 20% or less of its after-repair value.”*

The **Property Screening** tab is still not sent. Do not assume it is empty.

---

## Confirm before using the 20% rule

PIG-003 still says purchase price ≤ **20% of ARV**, not “20% below ARV.”

Example on a $400,000 ARV house:

- **As written (20% of ARV):** max offer about **$80,000**
- **If he meant 20% below ARV:** max offer about **$320,000**

Ask him to circle one. Do not guess.

MLS will not give a reliable ARV. Ask who supplies it, and when.

---

## Still needed — send this to Damian next

### A. Finish Pirates IG LLC (do this now)

Buy-box cities are in. We still need the **contact row** and the remaining blanks.

One Excel/CSV line:

1. Investor Name: Pirates IG LLC
2. Contact name (person we text)
3. Phone
4. Email
5. Preferred channel: SMS (or say otherwise)
6. May we text? Yes / No
7. May we email? Yes / No
8. Active? Yes / No
9. Notes

Then:

10. Circle one: **20% of ARV** or **20% below ARV**
11. Who supplies ARV, and when
12. Any max dollar price in addition to the ARV % — or “no dollar cap”
13. Min beds / baths / sq ft / year built — or “no minimum”
14. Occupancy and cash vs finance — or “any”
15. Screenshot or export of the **Property Screening** tab
16. Any other investors? If none, write “Pirates IG LLC is the only investor for now.”

Do not re-ask for property type, HOA, or the three cities.

### B. Alerts

1. Confirm Telegram for Approve / Reject / Snooze
2. Telegram username on 702-371-0950
3. Hours we may alert him
4. Alert on 90+ only, 80+, or 70+
5. Re-alert on price drop / back-on-market? Yes / No

### C. Live MLS (when ready to leave mock listings)

1. MLS name and his MLS agent ID
2. Written OK from him (as broker) to use the authorized API/feed — not the website
3. Vendor name or welcome email if the office has one
4. Statuses: Active only, or also Coming Soon / Back on Market
5. May we store remarks, photos, listing URL?

Watch area for listings can default to Las Vegas, North Las Vegas, and Henderson from PIG-004 unless he adds more.

### D. Investor texts (after Approve exists)

1. Written OK that we text only after he taps Approve
2. Twilio, or “set it up for me”
3. Outbound caller ID number
4. Sample text he already sends, if any
5. Note that Pirates IG LLC agreed to receive property texts

### E. Hold until real offers (does not block matching)

1. Blank forms he actually uses, with Yes/No: store / fill / send / e-sign
2. Transaction platform name
3. Two sample closed investor files, private data blacked out
4. Default earnest money, inspection days, closing timeline
5. Buyer name on contract: Pirates IG LLC vs ask every time

---

## Do not ask again

- His name, brokerage, license, phone, email
- Buyer-side investor role
- PIG-001 property type, PIG-002 no HOA, PIG-004 cities
- The wording of PIG-003 except the **of ARV vs below ARV** clarification

## Do not accept

- SSNs, bank logins, wire packets
- MLS website passwords in email
- Permission to scrape the MLS
- Guessing “20% of ARV” into “20% off ARV”
