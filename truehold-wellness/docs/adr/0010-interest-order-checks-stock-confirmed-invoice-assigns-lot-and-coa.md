# Interest order checks stock; paid invoice assigns lot and COA

Today a confirmed interest order decrements on-hand. Instead, the interest order only checks that inventory is available. On-hand is removed when the invoice is marked paid. That payment assigns the peptide lot and COA to the Client so we can track which clients received each peptide. Draft or issued-but-unpaid invoices do not move inventory.
