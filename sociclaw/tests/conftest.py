import json
from pathlib import Path

import pytest

from sociclaw.scripts.content_generator import GeneratedPost


@pytest.fixture
def sample_content() -> list:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "sample_content.json"
    # Some editors/tools may write JSON with UTF-8 BOM; handle both.
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture
def sample_generated_posts(sample_content) -> list:
    posts = []
    for item in sample_content:
        posts.append(
            GeneratedPost(
                text=item["text"],
                image_prompt=item["image_prompt"],
                hashtags=item["hashtags"],
                category=item["category"],
                date=item.get("date"),
                time=item.get("time"),
            )
        )
    return posts
