from pathlib import Path

from sociclaw.scripts.memory_store import SociClawMemoryStore, MemoryRecord


def test_memory_store_upsert_and_read_recent_topics(tmp_path):
    db_path = tmp_path / "memory.db"
    store = SociClawMemoryStore(db_path)

    store.upsert_generation(
        provider="telegram",
        provider_user_id="111",
        category="tips",
        topic="AI agents",
        text="Post about AI agents",
        has_image=True,
        with_logo=True,
    )
    store.upsert_generation(
        provider="telegram",
        provider_user_id="111",
        category="news",
        topic="crypto regulation",
        text="Regulation update",
        has_image=False,
        with_logo=False,
    )
    store.upsert_generation(
        provider="telegram",
        provider_user_id="222",
        category="tips",
        topic="other user",
    )

    topics = store.get_recent_topics(provider="telegram", provider_user_id="111", limit=5)
    assert topics == ["crypto regulation", "AI agents"]

    rows = store.get_recent_posts(provider="telegram", provider_user_id="111", limit=5)
    assert len(rows) == 2
    assert rows[0].topic == "crypto regulation"
    assert isinstance(rows[0], MemoryRecord)


def test_memory_store_distribution_and_clear(tmp_path):
    db_path = tmp_path / "memory.db"
    store = SociClawMemoryStore(db_path)

    store.upsert_generation(
        provider="telegram",
        provider_user_id="123",
        category="tips",
        topic="topic-1",
    )
    store.upsert_generation(
        provider="telegram",
        provider_user_id="123",
        category="news",
        topic="topic-2",
    )

    dist = store.get_category_distribution(provider="telegram", provider_user_id="123", days=1)
    assert dist["tips"] == 1
    assert dist["news"] == 1

    removed = store.clear_user(provider="telegram", provider_user_id="123")
    assert removed == 2
    assert store.get_recent_posts(provider="telegram", provider_user_id="123") == []
