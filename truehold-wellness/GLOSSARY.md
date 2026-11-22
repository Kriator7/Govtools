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
A record that a Client received one peptide line: lot, COA, paid invoice, and date. One paid invoice with two peptides is two rows, same Client name and THW-###.
_Avoid_: health app, interest order

**Connection**:
A way to reach a Client: email, phone, Telegram, or similar. Connections attach to the Client; they are not the Client's identity.
_Avoid_: Client name, THW-###
