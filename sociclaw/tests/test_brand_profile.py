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
        content_language="pt-BR",
        target_audience="Founders",
        value_proposition="Automate social output",
        key_themes=["Automation", "Growth"],
        do_not_say=["spam"],
        keywords=["SociClaw", "AI"],
        personality_traits=["Analítico", "Pragmático"],
        visual_style="clean and bold",
        signature_openers=["Aqui vai o que importa", "Sem enrolação"],
        content_goals=["Educar", "Conversar"],
        cta_style="question",
        has_brand_document=True,
        brand_document_path="/docs/brand.md",
    )

    saved = save_brand_profile(original, path)
    loaded = load_brand_profile(saved)

    assert loaded.name == "SociClaw"
    assert loaded.voice_tone == "Witty"
    assert loaded.content_language == "pt-BR"
    assert loaded.key_themes == ["Automation", "Growth"]
    assert loaded.keywords == ["SociClaw", "AI"]
    assert loaded.personality_traits == ["Analítico", "Pragmático"]
    assert loaded.visual_style == "clean and bold"
    assert loaded.signature_openers == ["Aqui vai o que importa", "Sem enrolação"]
    assert loaded.content_goals == ["Educar", "Conversar"]
    assert loaded.cta_style == "question"
    assert loaded.has_brand_document is True
    assert loaded.brand_document_path == "/docs/brand.md"


def test_content_generator_applies_brand_constraints(tmp_path):
    profile_path = tmp_path / "company_profile.md"
    save_brand_profile(
        BrandProfile(
            name="SociClaw",
            do_not_say=["shitcoin"],
            keywords=["SociClaw"],
            key_themes=["Crypto"],
            content_language="en",
            visual_style="clean and bold",
            signature_openers=["Quick take"],
            personality_traits=["practical", "direct"],
            content_goals=["conversation", "clarity"],
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
    assert "Visual Style: clean and bold" in post.details
    assert "Personality Traits: practical, direct" in post.details


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
            "--personality-traits",
            "Practical,Direct",
            "--visual-style",
            "Minimalist, bold, clean",
            "--signature-openers",
            "Quick take,No fluff",
            "--content-goals",
            "educate,build trust",
            "--cta-style",
            "question",
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
            "--content-language",
            "pt-BR",
            "--has-brand-document",
            "--brand-document-path",
            "/docs/brand.md",
            "--non-interactive",
        ]
    )

    rc = args.func(args)
    assert rc == 0

    loaded = load_brand_profile(Path(path))
    assert loaded.target_audience == "Creators"
    assert loaded.keywords == ["SociClaw", "AI"]
    assert loaded.personality_traits == ["Practical", "Direct"]
    assert loaded.visual_style == "Minimalist, bold, clean"
    assert loaded.signature_openers == ["Quick take", "No fluff"]
    assert loaded.content_goals == ["educate", "build trust"]
    assert loaded.cta_style == "question"
    assert loaded.content_language == "pt-BR"
    assert loaded.has_brand_document is True
