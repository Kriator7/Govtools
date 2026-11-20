Demo wallet keys follow the Cardano testnet docs: payment key, stake key, and a
Preprod base address (`--testnet-magic 1`). Generate with
`bash scripts/create_wallet.sh`.

Find the wallet later in **`keys/wallet-letter.txt`**. That letter copies the
addresses and key files into one 0600 file. It is gitignored. See
`WHERE-IS-THE-WALLET.md`. Do not commit `*.skey`, `*.vkey`, `*.addr`,
`wallet-letter.txt`, or signed transactions.

Sources:
- https://docs.cardano.org/cardano-testnets/getting-started
- https://developers.cardano.org/docs/operate-a-stake-pool/block-producer/generating-wallet-keys/
