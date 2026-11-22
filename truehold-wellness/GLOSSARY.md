# TrueHold Wellness

Order/inbox workflow on @THWellness_bot

## Language

**Client**:
A person on the Client sheet. Staff may add them before any purchase.
_Avoid_: Customer, Telegram visitor, interest-order contact

**THW-###**:
The stable identifier of a Client, minted automatically when an invoice introduces a name the Client sheet does not have.
_Avoid_: Telegram chat id, phone as id

**Interest-order contact**:
A person with a confirmed interest order. They are a Client only if they already have a Client sheet row.
_Avoid_: Client, customer

**Client sheet**:
The workbook sheet that is the record of Clients. Other sheets reference it; they do not store a second copy of the person.
_Avoid_: clients.json, invoice roster
_Alias_: Clients

**Client name**:
The unique name of a Client on the Client sheet. An invoice carries this name to find the row.
_Avoid_: customer_name, Telegram username
