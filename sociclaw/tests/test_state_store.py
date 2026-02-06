from pathlib import Path
import json

from sociclaw.scripts.state_store import StateStore


def test_state_store_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    store = StateStore(path)

    assert store.load() == {}

    u = store.upsert_user(provider="telegram", provider_user_id="123", image_api_key="sk1", wallet_address="0xabc")
    assert u.provider == "telegram"
    assert u.provider_user_id == "123"
    assert u.image_api_key == "sk1"
    assert u.wallet_address == "0xabc"
    assert u.created_at
    assert u.updated_at

    u2 = store.get_user(provider="telegram", provider_user_id="123")
    assert u2 is not None
    assert u2.image_api_key == "sk1"
    assert u2.wallet_address == "0xabc"

    # Update only wallet, keep key
    store.upsert_user(provider="telegram", provider_user_id="123", wallet_address="0xdef")
    u3 = store.get_user(provider="telegram", provider_user_id="123")
    assert u3 is not None
    assert u3.image_api_key == "sk1"
    assert u3.wallet_address == "0xdef"


def test_state_store_reads_legacy_provider_api_key(tmp_path: Path):
    path = tmp_path / "state.json"
    payload = {
        "version": 1,
        "updated_at": "2026-02-06T00:00:00Z",
        "users": {
            "telegram:123": {
                "provider": "telegram",
                "provider_user_id": "123",
                "legacy_provider_api_key": "sk_legacy",
                "wallet_address": "0xabc",
                "created_at": "2026-02-06T00:00:00Z",
                "updated_at": "2026-02-06T00:00:00Z",
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    store = StateStore(path)
    u = store.get_user(provider="telegram", provider_user_id="123")
    assert u is not None
    assert u.image_api_key == "sk_legacy"

