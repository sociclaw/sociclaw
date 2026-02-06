from pathlib import Path

from sociclaw.scripts.runtime_config import RuntimeConfig, RuntimeConfigStore


def test_runtime_config_store_roundtrip(tmp_path):
    path = tmp_path / "runtime_config.json"
    store = RuntimeConfigStore(path)

    cfg = RuntimeConfig(
        provider="telegram",
        provider_user_id="123",
        user_niche="crypto",
        posting_frequency="2/day",
        use_trello=True,
        use_notion=False,
        timezone="UTC",
    )
    saved = store.save(cfg)
    loaded = RuntimeConfigStore(Path(saved)).load()

    assert loaded.provider == "telegram"
    assert loaded.provider_user_id == "123"
    assert loaded.user_niche == "crypto"
    assert loaded.use_trello is True
