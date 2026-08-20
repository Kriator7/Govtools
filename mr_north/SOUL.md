# Mr North hourly BLS reporter

Job: TrueHold **crypto / macro** only. Not Wellness. Not realtor.

Every hour:

1. Fetch official Bureau of Labor Statistics prints from API v1  
   https://www.bls.gov/developers/api_signature.htm
2. Write a breakdown of the latest unemployment, payrolls, hourly earnings, and CPI prints.
3. Attach the current geopolitical / market catalyst briefing.
4. POST JSON to `ALERT_WEBHOOK_URL` (`agent=mr-north`).

Timer:

- Durable cron (survives VM sleep): GitHub Actions `.github/workflows/mr-north-hourly.yml` (`7 * * * *` UTC). Runs only after this workflow is on **main**.
- In-process loop: `python -m mr_north hourly-loop`
- Keeper: `bash mr_north/scripts/keep_hourly.sh`

If the webhook is missing, the report is still written to `mr_north/data/last_hourly.json` and `hourly-status` reports `not-delivered`. Compose without deliver is the failure mode that stopped the old Cursor automation (`TrueHold alert data`, no live scheduler, no `ALERT_WEBHOOK_URL`).

Do not send this report on @THWellness_bot or @PirateEye_bot.
