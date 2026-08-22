# Mr North reporter

Job: TrueHold **crypto / macro** only. Not Wellness. Not realtor.

North watches markets and delivers two report types to **both** Telegram locations:

1. The **larger** geopolitical / market catalyst briefing (group + second chat).
2. The **hourly** Bureau of Labor Statistics breakdown (same two chats).
3. **Immediate** BTC / threshold alerts when the print changes (same two chats).

Every hour:

1. Fetch official Bureau of Labor Statistics prints from API v1  
   https://www.bls.gov/developers/api_signature.htm
2. Write a breakdown of the latest unemployment, payrolls, hourly earnings, and CPI prints.
3. Attach the current geopolitical / market catalyst briefing.
4. `sendMessage` the report on **@Mr_North_bot** to every configured chat  
   (`NORTH_TELEGRAM_BOT_TOKEN` + `NORTH_TELEGRAM_CHAT_ID` + `NORTH_TELEGRAM_GROUP_CHAT_ID`).  
   Default group: `-1003939359929`. Never PirateEye (`-5372586958`).  
   https://core.telegram.org/bots/api#sendmessage
5. Optional extra: POST JSON to `ALERT_WEBHOOK_URL` (`agent=mr-north`).

Between hours:

- Poll BTC about every 5 minutes (CoinGecko simple price).
- Alert both chats immediately on a $65K watch-level cross or a ≥2% move.

Timer:

- Durable cron (survives VM sleep): GitHub Actions `.github/workflows/mr-north-hourly.yml` (`7 * * * *` UTC) and `.github/workflows/mr-north-watch.yml` (`*/15 * * * *`). Runs only after these workflows are on **main**.
- In-process loop: `python -m mr_north hourly-loop`
- Keeper: `bash mr_north/scripts/keep_hourly.sh`

If Telegram is not configured, the report is still written to `mr_north/data/last_hourly.json` and `hourly-status` reports `not-delivered`. Compose without deliver is the failure mode that stopped the old Cursor automation (`TrueHold alert data`, no live scheduler, no destination).

Do not send this report on any other Telegram bot. Live `getMe` must return `Mr_North_bot`.
