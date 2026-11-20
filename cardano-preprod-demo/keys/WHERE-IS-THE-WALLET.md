# Where is the Preprod wallet letter?

The funded demo wallet lives in this directory.

1. **Wallet letter (keys included, gitignored):** `keys/wallet-letter.txt`
2. **Payment address file:** `keys/payment.addr`
3. **Stake address file:** `keys/stake.addr`
4. **Signing keys:** `keys/payment.skey`, `keys/stake.skey`

Generate or refresh those files with:

```bash
bash scripts/create_wallet.sh
```

Network is Preprod only (`--testnet-magic 1`). Do not commit `wallet-letter.txt`,
`*.skey`, `*.vkey`, or `*.addr`.
