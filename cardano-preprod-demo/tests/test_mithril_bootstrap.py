from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "mithril_bootstrap.sh"
COMPOSE = ROOT / "docker-compose.yml"


def test_bootstrap_script_is_preprod_only() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert SCRIPT.exists()
    assert "https://aggregator.release-preprod.api.mithril.network/aggregator" in text
    assert "mithril-infra/configuration/release-preprod/genesis.vkey" in text
    assert "mithril-infra/configuration/release-preprod/ancillary.vkey" in text
    assert "--include-ancillary" in text
    assert "CARDANO_NETWORK=preprod" in text
    assert 'protocolMagicId' in text
    assert 'MAGIC" != "1"' in text
    assert "aggregator.release-mainnet" not in text
    assert "CARDANO_NETWORK=mainnet" not in text
    assert "Refusing mainnet" in text


def test_compose_stays_on_preprod() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert "NETWORK=preprod" in text
    assert "NETWORK=mainnet" not in text
    assert "cardano-preprod-node-db" in text
