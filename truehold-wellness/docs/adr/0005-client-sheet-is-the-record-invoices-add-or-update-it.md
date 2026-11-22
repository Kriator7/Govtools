# Client sheet is the record; invoices add or update it

Who is a Client is stored on a separate Clients workbook sheet, not in clients.json and not as duplicated people on Orders. Other workbook items reference that sheet. An issued invoice adds a Client row or updates the existing THW-### row. Interest-order contacts do not get a Client sheet row until the first invoice.
