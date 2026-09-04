---
name: pirateeye-open-leads
description: >
  Find investor homes for @PirateEye_bot without MLS access. Search public
  obituaries, FSBO RSS, HUD/REO mentions, and probate/foreclosure notices in
  Clark County. Use when Damian needs listings and MLS is still mock.
---

# PirateEye open-lead hunt

TrueHold Wellness and Mr North are other companies. This skill is **@PirateEye_bot** / `realtor-agent/` only.

MLS (`MLS_PROVIDER=mock`) is not a usable listing feed until Damian or the broker authorizes Trestle/IDX. Do **not** scrape Matrix, Zillow, Redfin, or Gmail listing emails.

## What to run

From `realtor-agent/`:

```bash
python -m app.cli hunt
python -m app.cli hunt --source obituary
python -m app.cli hunt --source fsbo
```

On Telegram (operator chat after `/start`):

1. `/hunt` — all public sources
2. `/obits` — Clark County obituaries (estate-watch)
3. `/fsbo` — Las Vegas for-sale-by-owner (Craigslist RSS)
4. `/hud` — HUD / government REO mentions
5. `/leads` — stored leads
6. `/mls` — honest MLS status (still mock)

## Sources (public only)

| Source | Feed | Use |
| --- | --- | --- |
| Obituaries | Google News RSS for Las Vegas / Clark County obituaries | Estate-watch. Families often sell. **Review only — never auto-contact next of kin.** Give Damian the obituary link and a Clark County Assessor search. |
| FSBO | Craigslist Las Vegas `reo` RSS (`format=rss`) | Homes owners are already advertising. Convert to a listing when address + price parse. |
| HUD / REO | Google News RSS for HUD / government-owned Las Vegas homes | Public inventory mentions, not Matrix. |
| Probate / trustee / foreclosure notices | Google News RSS | Public legal notices that a property may come to market. |

Official assessor portal (do not scrape): https://www.clarkcountynv.gov/government/departments/assessor/

Google News RSS: https://news.google.com/rss/search?q=…&hl=en-US&gl=US&ceid=US:en  
Craigslist RSS: https://lasvegas.craigslist.org/search/reo?format=rss

## Rules

1. Public RSS / documented government pages only. No MLS website scrape.
2. Obituary leads stay `review_only`. Damian researches the assessor; the bot does not call the family.
3. Investor notify still requires Telegram APPROVE. Hunt does not skip realtor review.
4. If a live HTTP fetch fails, say so and keep fixture/demo leads out of the live chat unless `OPEN_LEADS_MODE=fixture`.
5. Do not mix Wellness tokens or Mr North webhooks into this hunt.
