"""TrueHold Wellness payment invoice from a supplied merchandise subtotal.

Never invents SKU prices or tax. Delivery is the only priced rule in this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

from wellness_agent.delivery import (
    FREE_DELIVERY_THRESHOLD,
    INVOICE_SMALL_PRINT,
    LOCAL_DELIVERY_FEE,
    delivery_charge,
    format_usd,
    money,
    qualifies_for_free_delivery,
)
from wellness_agent.telegram_copy import TEAM_EMAIL

PACIFIC = ZoneInfo("America/Los_Angeles")

FULFILLMENT_LABELS = {
    "prep": "Las Vegas prep + local delivery",
    "delivery": "Las Vegas local delivery",
    "pickup": "Pickup",
    "ship": "Ship dry vials",
    "shipping": "Ship dry vials",
}


@dataclass(frozen=True)
class InvoiceQuote:
    invoice_id: str
    generated_at: str
    fulfillment: str
    fulfillment_label: str
    detail: str
    merchandise_subtotal: str
    delivery_fee: str
    delivery_waived: bool
    total: str
    small_print: str
    payment_note: str


def quote_invoice(
    *,
    merchandise_subtotal: Any,
    fulfillment: str = "delivery",
    invoice_id: str = "",
    detail: str = "Merchandise",
    when: datetime | None = None,
) -> InvoiceQuote:
    """Build invoice money lines from a caller-supplied merchandise subtotal."""
    subtotal = money(merchandise_subtotal)
    method = str(fulfillment or "delivery").strip().lower() or "delivery"
    fee = delivery_charge(merchandise_subtotal=subtotal, fulfillment=method)
    waived = method not in {"pickup", "ship", "shipping"} and qualifies_for_free_delivery(subtotal)
    stamp = when or datetime.now(tz=PACIFIC)
    label = FULFILLMENT_LABELS.get(method, FULFILLMENT_LABELS["delivery"])
    payment_note = (
        "Local Las Vegas: Zelle on the confirmation call. Prefer debit card? "
        "Pay on the website after the team confirms."
    )
    return InvoiceQuote(
        invoice_id=invoice_id or stamp.strftime("THW-INV-%Y%m%d-%H%M%S"),
        generated_at=stamp.strftime("%Y-%m-%d %H:%M %Z"),
        fulfillment=method,
        fulfillment_label=label,
        detail=str(detail or "Merchandise").strip() or "Merchandise",
        merchandise_subtotal=format_usd(subtotal),
        delivery_fee=format_usd(fee),
        delivery_waived=waived,
        total=format_usd(subtotal + fee),
        small_print=INVOICE_SMALL_PRINT,
        payment_note=payment_note,
    )


def format_invoice_text(quote: InvoiceQuote) -> str:
    delivery_note = quote.delivery_fee
    if quote.delivery_waived:
        delivery_note = f"{quote.delivery_fee}  (FREE — merchandise {format_usd(FREE_DELIVERY_THRESHOLD)}+)"
    elif quote.fulfillment in {"pickup", "ship", "shipping"}:
        delivery_note = f"{quote.delivery_fee}  (not the ${LOCAL_DELIVERY_FEE:.0f} local-delivery fee)"
    lines = [
        "TrueHold Wellness — invoice",
        "",
        f"Invoice: {quote.invoice_id}",
        f"Issued: {quote.generated_at}",
        f"Fulfillment: {quote.fulfillment_label}",
        "",
        f"{quote.detail}: {quote.merchandise_subtotal}",
        f"Local delivery: {delivery_note}",
        f"Total due: {quote.total}",
        "",
        quote.payment_note,
        "",
        quote.small_print,
        "",
        f"Questions: {TEAM_EMAIL} · (702) 879-8783",
        "Educational research-peptide information. Las Vegas residents for prep and local delivery.",
        "SKU prices are confirmed on the call. This form does not invent them.",
    ]
    return "\n".join(lines) + "\n"


def format_invoice_html(quote: InvoiceQuote) -> str:
    delivery_label = "Local delivery"
    delivery_extra = ""
    if quote.delivery_waived:
        delivery_label = "Local delivery (waived)"
        delivery_extra = (
            f'<div class="saved">You saved {format_usd(LOCAL_DELIVERY_FEE)} — '
            f"merchandise {format_usd(FREE_DELIVERY_THRESHOLD)}+</div>"
        )
    elif quote.fulfillment == "pickup":
        delivery_label = "Local delivery (pickup)"
    elif quote.fulfillment in {"ship", "shipping"}:
        delivery_label = "Local delivery (not charged on dry-vial shipping)"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TrueHold Wellness invoice {escape(quote.invoice_id)}</title>
<style>
  :root {{
    --navy: #0b1f3a;
    --gold: #c9a227;
    --cream: #f6f1e4;
    --ink: #1b2430;
    --muted: #6b6458;
  }}
  body {{
    margin: 0;
    background: #e8e2d2;
    color: var(--ink);
    font-family: "Iowan Old Style", Palatino, "Palatino Linotype", serif;
  }}
  .sheet {{
    max-width: 720px;
    margin: 24px auto;
    background: #fffdf8;
    border: 2px solid var(--navy);
    box-shadow: 0 8px 24px rgba(11, 31, 58, 0.12);
  }}
  header {{
    background: var(--navy);
    color: var(--cream);
    padding: 28px 36px 22px;
  }}
  header .kicker {{
    color: var(--gold);
    letter-spacing: 0.18em;
    font-size: 12px;
    font-family: "Avenir Next", "Segoe UI", sans-serif;
    text-transform: uppercase;
  }}
  h1 {{
    margin: 8px 0 0;
    font-size: 28px;
    font-weight: 600;
  }}
  .meta, .lines, .pay, footer {{
    padding: 20px 36px;
  }}
  .meta {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 24px;
    font-size: 15px;
    border-bottom: 1px solid #ddd4c0;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 16px;
  }}
  th {{
    text-align: left;
    font-family: "Avenir Next", "Segoe UI", sans-serif;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    padding-bottom: 8px;
  }}
  td {{
    padding: 10px 0;
    border-top: 1px solid #eee6d6;
  }}
  td.amt, th.amt {{
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}
  .total td {{
    font-size: 20px;
    font-weight: 700;
    border-top: 2px solid var(--navy);
  }}
  .saved {{
    color: #2f6b3c;
    font-size: 13px;
    margin-top: 4px;
  }}
  .pay {{
    background: var(--cream);
    font-size: 15px;
  }}
  footer {{
    padding-top: 8px;
    padding-bottom: 28px;
  }}
  .small-print {{
    font-size: 11px;
    line-height: 1.45;
    color: var(--muted);
    letter-spacing: 0.01em;
  }}
  .fine {{
    margin-top: 10px;
    font-size: 10px;
    color: #8a8378;
  }}
</style>
</head>
<body>
  <article class="sheet">
    <header>
      <div class="kicker">TrueHold Wellness</div>
      <h1>Invoice</h1>
    </header>
    <section class="meta">
      <div><strong>Invoice</strong><br>{escape(quote.invoice_id)}</div>
      <div><strong>Issued</strong><br>{escape(quote.generated_at)}</div>
      <div><strong>Fulfillment</strong><br>{escape(quote.fulfillment_label)}</div>
      <div><strong>Pay</strong><br>Zelle on the call · debit on the site</div>
    </section>
    <section class="lines">
      <table>
        <thead>
          <tr><th>Description</th><th class="amt">Amount</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>{escape(quote.detail)}</td>
            <td class="amt">{escape(quote.merchandise_subtotal)}</td>
          </tr>
          <tr>
            <td>{escape(delivery_label)}{delivery_extra}</td>
            <td class="amt">{escape(quote.delivery_fee)}</td>
          </tr>
          <tr class="total">
            <td>Total due</td>
            <td class="amt">{escape(quote.total)}</td>
          </tr>
        </tbody>
      </table>
    </section>
    <section class="pay">{escape(quote.payment_note)}</section>
    <footer>
      <p class="small-print">{escape(quote.small_print)}</p>
      <p class="fine">
        {escape(TEAM_EMAIL)} · (702) 879-8783 · Educational research-peptide information.
        Las Vegas residents for prep and local delivery. SKU prices are confirmed on the call.
      </p>
    </footer>
  </article>
</body>
</html>
"""
