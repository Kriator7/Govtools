# Mr North reporter

Job: TrueHold **economics / trading** only.

North delivers every report to **two** Telegram locations:

1. James personally (`NORTH_TELEGRAM_CHAT_ID`, default `1150046483`).
2. **MaximumMint & North** (`NORTH_TELEGRAM_GROUP_CHAT_ID`, default `-1003939359929`).

Never the PirateEye realtor group (`-5372586958`, MaximumMint & Agent Real).

Every hour:

1. Fetch official Bureau of Labor Statistics prints from API v1  
   https://www.bls.gov/developers/api_signature.htm
2. Write a breakdown of the latest unemployment, payrolls, hourly earnings, and CPI prints.
3. Attach the current geopolitical / market catalyst briefing.
4. `sendMessage` on **@Mr_North_bot** to both destinations above.  
   https://core.telegram.org/bots/api#sendmessage
5. Optional extra: POST JSON to `ALERT_WEBHOOK_URL` (`agent=mr-north`).

Between hours:

- Poll BTC about every 5 minutes (CoinGecko simple price).
- Alert both destinations immediately on a $65K watch-level cross or a ≥2% move.

If MaximumMint & North does not receive the message, delivery is a failure even if the personal chat succeeded.

Timer:

- Durable cron (survives VM sleep): GitHub Actions `.github/workflows/mr-north-hourly.yml` (`7 * * * *` UTC) and `.github/workflows/mr-north-watch.yml` (`*/15 * * * *`). Runs only after these workflows are on **main**.
- In-process loop: `python -m mr_north hourly-loop`
- Keeper: `bash mr_north/scripts/keep_hourly.sh`

Live `getMe` must return `Mr_North_bot`.
