# TrueHold Wellness

Order/inbox workflow on @THWellness_bot

## Language

**Client**:
A person TrueHold Wellness has issued an invoice to for peptide use.
_Avoid_: Customer, Telegram visitor, interest-order contact

**THW-###**:
The stable identifier of a Client, minted automatically when an invoice introduces a name the Client sheet does not have.
_Avoid_: Telegram chat id, phone as id

**Interest-order contact**:
A person who has a confirmed interest order but has not yet been issued a peptide invoice.
_Avoid_: Client, customer

**Client sheet**:
The workbook sheet that is the record of Clients. Other sheets reference it; they do not store a second copy of the person.
_Avoid_: clients.json, invoice roster
_Alias_: Clients
