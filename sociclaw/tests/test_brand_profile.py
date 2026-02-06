from datetime import datetime
from pathlib import Path

from sociclaw.scripts.brand_profile import BrandProfile, load_brand_profile, save_brand_profile
from sociclaw.scripts.content_generator import ContentGenerator
from sociclaw.scripts.scheduler import PostPlan
from sociclaw.scripts.cli import build_parser


def test_brand_profile_roundtrip(tmp_path):
    path = tmp_path / "company_profile.md"
    original = BrandProfile(
        name="SociClaw",
        slogan="Ship posts daily",
        voice_tone="Witty",
        target_audience="Founders",
        value_proposition="Automate social output",
        key_themes=["Automation", "Growth"],
        do_not_say=["spam"],
        keywords=["SociClaw", "AI"],
    )

    saved = save_brand_profile(original, path)
    loaded = load_brand_profile(saved)

    assert loaded.name == "SociClaw"
    assert loaded.voice_tone == "Witty"
    assert loaded.key_themes == ["Automation", "Growth"]
    assert loaded.keywords == ["SociClaw", "AI"]


def test_content_generator_applies_brand_constraints(tmp_path):
    profile_path = tmp_path / "company_profile.md"
    save_brand_profile(
        BrandProfile(
            name="SociClaw",
            do_not_say=["shitcoin"],
            keywords=["SociClaw"],
            key_themes=["Crypto"],
        ),
        profile_path,
    )

    generator = ContentGenerator(brand_profile_path=profile_path)
    plan = PostPlan(
        date=datetime.utcnow(),
        time=13,
        category="tips",
        topic="shitcoin risk management",
        hashtags=["Crypto", "Web3", "DYOR"],
    )

    post = generator.generate_post(plan)

    assert "shitcoin" not in post.text.lower()
    assert "sociclaw" in post.text.lower()
    assert "brand SociClaw" in post.image_prompt


def test_cli_briefing_non_interactive(tmp_path):
    path = tmp_path / "company_profile.md"
    parser = build_parser()
    args = parser.parse_args(
        [
            "briefing",
            "--path",
            str(path),
            "--name",
            "SociClaw",
            "--slogan",
            "Post faster",
            "--voice-tone",
            "Professional",
            "--target-audience",
            "Creators",
            "--value-proposition",
            "Save time",
            "--key-themes",
            "Growth,Automation",
            "--do-not-say",
            "spam",
            "--keywords",
            "SociClaw,AI",
        ]
    )

    rc = args.func(args)
    assert rc == 0

    loaded = load_brand_profile(Path(path))
    assert loaded.target_audience == "Creators"
    assert loaded.keywords == ["SociClaw", "AI"]
