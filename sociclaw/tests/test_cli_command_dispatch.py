import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from sociclaw.scripts.cli import build_parser
from sociclaw.scripts.content_generator import GeneratedPost
from sociclaw.scripts.runtime_config import RuntimeConfig, RuntimeConfigStore
from sociclaw.scripts.state_store import StateStore


def test_cli_home_without_subcommand(capsys):
    parser = build_parser()
    args = parser.parse_args([])
    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["agent"] == "SociClaw"


def test_cli_plan_generates_local_plan_file(tmp_path, capsys):
    cfg_path = tmp_path / "runtime_config.json"
    plan_path = tmp_path / "planned_posts.json"
    RuntimeConfigStore(cfg_path).save(
        RuntimeConfig(
            provider="telegram",
            provider_user_id="123",
            user_niche="ai agents",
            posting_frequency="1/day",
            use_trello=False,
            use_notion=False,
        )
    )

    parser = build_parser()
    args = parser.parse_args(
        [
            "plan",
            "--config-path",
            str(cfg_path),
            "--plan-path",
            str(plan_path),
            "--days",
            "1",
            "--posts-per-day",
            "1",
            "--skip-research",
        ]
    )

    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["planned_posts"] == 1
    assert plan_path.exists()


def test_cli_generate_uses_logo_and_attaches_to_trello(tmp_path, capsys, monkeypatch):
    cfg_path = tmp_path / "runtime_config.json"
    state_path = tmp_path / "state.json"
    plan_path = tmp_path / "planned_posts.json"

    RuntimeConfigStore(cfg_path).save(
        RuntimeConfig(
            provider="telegram",
            provider_user_id="123",
            brand_logo_url="https://cdn.example.com/logo.png",
            posting_frequency="1/day",
            use_trello=True,
        )
    )
    StateStore(state_path).upsert_user(provider="telegram", provider_user_id="123", image_api_key="sk_user")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    post = GeneratedPost(
        text="Test post",
        image_prompt="Futuristic social media dashboard",
        title="Test post",
        body="Body",
        details="Details",
        hashtags=["SociClaw"],
        category="tips",
        date=today,
        time=13,
    )
    plan_path.write_text(json.dumps({"version": 1, "posts": [asdict(post)]}, indent=2), encoding="utf-8")

    captured = {}

    class FakeImageGenerator:
        def __init__(self, **kwargs):
            self.image_url = kwargs.get("image_url")

        def generate_image(self, prompt: str, user_address: str):
            captured["prompt"] = prompt
            captured["user_address"] = user_address
            return type("ImageResult", (), {"url": "https://img.test/1.png", "local_path": None})()

    class FakeTrelloSync:
        def setup_board(self):
            return None

        def attach_image_to_post(self, generated_post, image_url=None, image_path=None):
            captured["attached_image_url"] = image_url
            return type("Card", (), {"id": "card_1"})()

        def create_card(self, generated_post):
            return type("Card", (), {"id": "card_1"})()

    monkeypatch.setattr("sociclaw.scripts.cli.ImageGenerator", FakeImageGenerator)
    monkeypatch.setattr("sociclaw.scripts.cli.TrelloSync", FakeTrelloSync)

    parser = build_parser()
    args = parser.parse_args(
        [
            "generate",
            "--config-path",
            str(cfg_path),
            "--state-path",
            str(state_path),
            "--plan-path",
            str(plan_path),
            "--count",
            "1",
            "--with-image",
            "--sync-trello",
        ]
    )

    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["generated"] == 1
    assert payload["remaining_planned_posts"] == 0
    assert captured["attached_image_url"] == "https://img.test/1.png"
    assert "Use the attached logo image" in captured["prompt"]


def test_cli_pay_alias_uses_runtime_identity(tmp_path, monkeypatch):
    cfg_path = tmp_path / "runtime_config.json"
    RuntimeConfigStore(cfg_path).save(RuntimeConfig(provider="telegram", provider_user_id="123"))

    called = {}

    def fake_topup_start(args):
        called["provider"] = args.provider
        called["provider_user_id"] = args.provider_user_id
        called["amount_usd"] = args.amount_usd
        return 0

    monkeypatch.setattr("sociclaw.scripts.cli.cmd_topup_start", fake_topup_start)

    parser = build_parser()
    args = parser.parse_args(["pay", "--config-path", str(cfg_path), "--amount-usd", "5"])
    rc = args.func(args)
    assert rc == 0
    assert called["provider"] == "telegram"
    assert called["provider_user_id"] == "123"
