"""Tests for UI rebrand, Kirana demo prompts, and fixture generation scaffolding (gp-005)."""

import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_ui_index_contains_rebrand_elements(client: TestClient):
    """GET / must return 200 and contain Kirana rebrand, Gnani models, and Shivani voice."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "Kirana Voice Agent" in html
    assert "Prisma" in html
    assert "Timbre" in html
    assert "Shivani" in html


def test_ui_index_contains_three_example_prompts(client: TestClient):
    """GET / must contain the 3 canonical Hinglish demo prompts from specs.md §4."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    prompt1 = "Bhaiya, 2 kilo atta kitne ka hai?"
    prompt2 = "2 kilo atta aur 1 litre tel le lo, total kitna hua?"
    prompt3 = "Doodh hai kya stock mein?"

    assert prompt1 in html
    assert prompt2 in html
    assert prompt3 in html


def test_ui_index_contains_synthetic_data_footer(client: TestClient):
    """GET / must contain the required synthetic data disclaimer and Gnani model note."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "Demo uses synthetic kirana data only — no real customers or phone numbers." in html
    assert "Gnani models: Prisma v2.5 STT · Timbre v3.0 TTS" in html


def test_demo_prompts_markdown_exists_and_covers_five_turns():
    """demo/demo-prompts.md must exist and detail all 5 demo turns for the 2-3 minute cut."""
    prompts_file = ROOT_DIR / "demo" / "demo-prompts.md"
    assert prompts_file.exists(), "demo/demo-prompts.md does not exist"

    content = prompts_file.read_text(encoding="utf-8")
    assert "Turn 1" in content
    assert "Turn 2" in content
    assert "Turn 3" in content
    assert "Turn 4" in content
    assert "Turn 5" in content

    # All 5 turns must be documented with prompt / reply
    assert "Bhaiya, 2 kilo atta kitne ka hai?" in content
    assert "2 kilo atta aur 1 litre tel le lo, total kitna hua?" in content
    assert "Doodh hai kya stock mein?" in content
    assert "chai patti" in content.lower()
    assert "Prisma" in content
    assert "Timbre" in content


def test_generate_fixtures_script_syntax_and_refusal_without_key():
    """demo/generate_fixtures.py must compile cleanly and exit non-zero without GNANI_API_KEY."""
    script_path = ROOT_DIR / "demo" / "generate_fixtures.py"
    assert script_path.exists(), "demo/generate_fixtures.py does not exist"

    # Syntax check
    source = script_path.read_text(encoding="utf-8")
    compile(source, str(script_path), "exec")

    # Run in subprocess with clean environment (no GNANI_API_KEY)
    clean_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": str(ROOT_DIR / "src"),
    }
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        env=clean_env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode != 0, "Script should exit non-zero when GNANI_API_KEY is not set"
    error_output = proc.stderr + proc.stdout
    assert "GNANI_API_KEY" in error_output


def test_demo_readme_exists_and_documents_voice_swap():
    """demo/README.md must exist and explain fixtures, voice swap, and gp-006 role."""
    readme_path = ROOT_DIR / "demo" / "README.md"
    assert readme_path.exists(), "demo/README.md does not exist"

    text = readme_path.read_text(encoding="utf-8")
    assert "Timbre" in text
    assert "gp-006" in text
    assert "narration" in text.lower() or "voice" in text.lower()


def test_zero_green_grid_references_in_src_and_tests():
    """Verify zero remaining legacy scenario references in python, html, or js files."""
    extensions = {".py", ".html", ".js"}
    targets = [ROOT_DIR / "src", ROOT_DIR / "tests"]
    matches = []
    pattern_a = "Green" + " Grid"
    pattern_b = "Green" + "Grid"
    this_file = Path(__file__).resolve()

    for target in targets:
        for p in target.rglob("*"):
            if p.suffix in extensions and p.is_file() and p.resolve() != this_file:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    if pattern_a in line or pattern_b in line:
                        matches.append(f"{p}:{line_idx}: {line.strip()}")

    assert not matches, "Found unexpected legacy references:\n" + "\n".join(matches)
