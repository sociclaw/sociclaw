from pathlib import Path

from sociclaw.scripts.release_audit import scan_forbidden_terms, scan_placeholders


def test_scan_placeholders(tmp_path):
    root = tmp_path
    (root / "README.md").write_text("clone https://github.com/<your-org>/repo\n", encoding="utf-8")
    findings = scan_placeholders(root)
    assert len(findings) == 1
    assert findings[0].kind == "placeholder"


def test_scan_forbidden_terms(tmp_path):
    root = tmp_path
    (root / "doc.md").write_text("This references ExampleUpstream backend.\n", encoding="utf-8")
    findings = scan_forbidden_terms(root, ["ExampleUpstream"])
    assert len(findings) == 1
    assert findings[0].kind == "forbidden_term"
    assert findings[0].file == str(Path("doc.md"))
