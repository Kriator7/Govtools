# Client sheet is the record; invoices add or update it

Who is a Client is stored on a separate Clients workbook sheet, not in clients.json and not as duplicated people on Orders. Other workbook items reference that sheet. Staff may add a Client before any invoice. An issued invoice updates the matching Client name or adds a row if the name is new.
