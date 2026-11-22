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
