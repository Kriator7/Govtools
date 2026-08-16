# Govtools

Two separate TrueHold agents. Do not mix their alerts, copy, or webhooks.

## TrueHold crypto agent

`truehold/crypto_agent` sends crypto and macro alerts only. When any crypto alert fires, the outbound message and JSON also include the current geopolitical / market catalyst briefing (Hormuz, money-flow, BTC/regime status, oil–yields–DXY).

It does **not** send Wellness orders, inbox, peptides, fulfillment, or other business-email content.

```bash
python -m pip install -e ".[dev]"
python -m truehold.crypto_agent compose
python -m truehold.crypto_agent send --dry-run --type btc_threshold
ALERT_WEBHOOK_URL=https://example.invalid/crypto python -m truehold.crypto_agent send --type btc_threshold
```

## TrueHold Wellness agent

`truehold/wellness_agent` sends business-inbox alerts only. Every Wellness alert includes a **complete** snapshot so none of these are dropped:

- orders
- payments
- fulfillment requests
- shipping issues
- cancellations/refunds
- peptide messages
- other actionable business email

The snapshot is stored in `truehold/wellness_agent/data/current_inbox.json`. Missing categories fail closed.

```bash
python -m truehold.wellness_agent compose
python -m truehold.wellness_agent compose --type order --detail "New TrueHold Wellness order received."
python -m truehold.wellness_agent send --dry-run --type business
WELLNESS_ALERT_WEBHOOK_URL=https://example.invalid/wellness python -m truehold.wellness_agent send --type order
```

Wellness uses `WELLNESS_ALERT_WEBHOOK_URL` only. It does not read `ALERT_WEBHOOK_URL`.

## Tests

```bash
python -m pytest
```
