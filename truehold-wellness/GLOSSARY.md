# TrueHold Wellness

Order/inbox workflow on @THWellness_bot

## Language

**Client**:
A person on the Client sheet. Staff may add them before any purchase.
_Avoid_: Customer, Telegram visitor, interest-order contact

**THW-###**:
An invoice identifier. THW means TrueHold Wellness; the digits are that invoice's number.
_Avoid_: Client id, Client name

**Interest-order contact**:
A person with a confirmed interest order. They are a Client only if they already have a Client sheet row.
_Avoid_: Client, customer

**Client sheet**:
The workbook sheet that is the record of Clients. Other sheets reference it; they do not store a second copy of the person.
_Avoid_: clients.json, invoice roster
_Alias_: Clients

**Client name**:
The unique name that identifies a Client on the Client sheet. Invoices and other sheets use this name to find the person.
_Avoid_: customer_name, Telegram username, THW-###

**Interest order**:
A request to buy a peptide before an invoice. It confirms the peptide is available; it does not remove inventory.
_Avoid_: purchase, checkout
_Alias_: _place_interest_order

**Lot**:
A specific manufactured batch of a peptide. A paid invoice assigns a lot to a Client.
_Avoid_: SKU, on-hand

**COA**:
The Certificate of Analysis for a lot, kept with the Client assignment so we know which clients received which peptide.
_Avoid_: locked information sheet

**Paid invoice**:
An invoice marked paid. That is when on-hand is removed and lot and COA are assigned to the Client.
_Avoid_: draft invoice, issued unpaid invoice

**Peptide use**:
A record that a Receiving Client received one peptide line: lot, COA, paid invoice, and date. One paid invoice with two peptides is two rows.
_Avoid_: interest order, 12-month plan

**Connection**:
A way to reach a Client: email, phone, Telegram, or similar. Connections attach to the Client; they are not the Client's identity.
_Avoid_: Client name, THW-###

**Client tracker**:
The app that holds a Client's chief complaint, body measurements, 12-month plan, connections, and peptide use history.
_Avoid_: clients.json, peptide-use-only sheet

**Chief complaint**:
The Client's primary reason for working with TrueHold Wellness, stored on the Client tracker.
_Avoid_: notes, peptide use

**12-month plan**:
The Client's roadmap on the Client tracker. Each purchase updates this plan.
_Avoid_: peptide use row

**Check-in**:
An agent message to the Client one week before they are due to reorder: how they feel, improvement, concerns, questions, and a free consult offer.
_Avoid_: payment request

**Reorder due**:
Supply months after the Client's latest paid invoice that counts as their own supply. A newer such payment resets the clock. Check-in is one week before this date.
_Avoid_: interest order date, invoice issue date

**Supply months**:
How long a paid invoice covers for the Client named on it. Default is one month. Staff may rarely set two months, for example travel.
_Avoid_: interest order duration

**Receiving Client**:
The Client a peptide line is for. Defaults to the invoice Client name. A friend vial names someone else.
_Avoid_: payer, Telegram chat
