# Cardano Preprod demo

Local **Preprod** (`networkMagic` 1) node from the official IntersectMBO
Docker image, plus a payment GUI that talks to the node socket. Sending stays
disabled until `syncProgress` is `100.00`. There is no Blockfrost path.

## Sources

1. Compose template: [IntersectMBO/cardano-node `docker-compose.yml` @ 11.1.3](https://github.com/IntersectMBO/cardano-node/blob/11.1.3/docker-compose.yml)
2. `NETWORK=preprod` scripts mode: [nix/docker/README.md @ 11.1.3](https://github.com/IntersectMBO/cardano-node/blob/11.1.3/nix/docker/README.md)
3. Preprod configs compatible with node 11.1.3: [Cardano Operations Book — Pre-production](https://book.world.dev.cardano.org/env-preprod.html)
4. Release + checksums: [cardano-node 11.1.3](https://github.com/IntersectMBO/cardano-node/releases/tag/11.1.3) (`sha256sums.txt`)
5. Tip query: `cardano-cli query tip --testnet-magic 1 --socket-path <socket>`
6. Mithril bootstrap: [Getting started — bootstrap a Cardano node](https://mithril.network/doc/manual/getting-started/bootstrap-cardano-node)
7. Preprod aggregator: `https://aggregator.release-preprod.api.mithril.network/aggregator`
8. Preprod vkeys: [IntersectMBO/mithril `mithril-infra/configuration/release-preprod`](https://github.com/IntersectMBO/mithril/tree/main/mithril-infra/configuration/release-preprod)

`NETWORK` is hardcoded to `preprod` in `docker-compose.yml`. Do not point this
stack at mainnet. Genesis replay from slot 0 is slow even on Preprod; use the
Mithril snapshot before expecting `syncProgress` `100.00`.

Pinned images:

- `ghcr.io/intersectmbo/cardano-node:11.1.3@sha256:c526d01a6d5c866a05109f0e79cca6a4c0e90fd359f846cc983a788f320bf570`
- `ghcr.io/intersectmbo/cardano-submit-api:11.1.3@sha256:1b277c73098aef0270e30a1169d922e7dbc9db8db2fc0a9952136dc86635cac4`

Persistent ledger: Docker volume `cardano-preprod-node-db` → `/data/db`.
IPC socket: `./ipc/node.socket` (bind-mounted at `/ipc` in the container).
The node uses `network_mode: host` because Docker bridge NAT timed out to
Preprod peers in this environment; the host TCP path to those peers works.

## Run

```bash
cd cardano-preprod-demo
bash scripts/up.sh
```

1. Starts Compose project `cardano-preprod-demo`.
2. Installs `cardano-cli` from the 11.1.3 tarball after sha256 verification.
3. Queries tip on magic 1.
4. Serves the payment GUI at `http://127.0.0.1:8787`.

Fast-sync the persistent volume from the official **release-preprod** Mithril
snapshot (includes ancillary ledger files; client distribution `2642.0`):

```bash
bash scripts/mithril_bootstrap.sh
```

That script refuses mainnet aggregators, checks `protocolMagicId=1` before
replacing `cardano-preprod-node-db`, then restarts the node. Sending stays
disabled until `query tip --testnet-magic 1` reports `syncProgress` `100.00`.

Tip only:

```bash
bash scripts/query_tip.sh
```

Tests (no live node required):

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

The demo wallet is a Preprod **base address** (payment + stake keys), built with
`bash scripts/create_wallet.sh` from the [testnet getting-started](https://docs.cardano.org/cardano-testnets/getting-started)
commands (`--testnet-magic 1`). Fund it from the [Preprod faucet](https://docs.cardano.org/cardano-testnets/tools/faucet)
(`Environment: Preprod Testnet`, action `Receive test ADA`). The wallet letter
with addresses and keys is `keys/wallet-letter.txt` (gitignored, mode 0600).
See `keys/WHERE-IS-THE-WALLET.md`. Unused tADA should be returned to the faucet
address published on that page.
