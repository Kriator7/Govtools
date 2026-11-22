# Client is a person, not a Telegram chat

Wellness currently keys clients.json by Telegram chat_id. We decided a Client is a person; chats and invoices attach to them. Chat-keyed identity cannot represent one person with two chats, or an invoice client with no Telegram yet.
