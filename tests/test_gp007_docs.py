"""Tests for gp-007: Demo script (2-3 min) + PITCH.md + README rewrite + docs hygiene."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_readme_contains_gnani_kirana_and_no_legacy_project():
    """README.md must reflect gnani-voicepilot: Kirana Voice Agent, Prisma, Timbre, Shivani, no legacy project, no Gradio."""
    readme_path = ROOT_DIR / "README.md"
    assert readme_path.exists(), "README.md must exist"
    content = readme_path.read_text(encoding="utf-8")

    assert "Kirana Voice Agent" in content
    assert "Prisma v2.5" in content
    assert "Timbre v3.0" in content
    assert "Shivani" in content
    assert "hi-IN" in content
    assert "hi-en" in content
    assert "PITCH.md" in content

    # Must NOT contain legacy references
    legacy_pattern_a = "green" + " grid"
    legacy_pattern_b = "green" + "grid"
    assert legacy_pattern_a not in content.lower()
    assert legacy_pattern_b not in content.lower()

    # Must NOT claim Gradio or Evon LLM
    assert "gradio" not in content.lower(), "README must not claim Gradio (FastAPI + static HTML/JS UI only)"
    assert "evon" not in content.lower(), "README must not claim Evon LLM (not on Gnani API platform)"

    # Must document the verified live-smoke latencies
    assert "4,889.0" in content or "4889.0" in content
    assert "2,171.9" in content or "2171.9" in content
    assert "7,579.1" in content or "7579.1" in content


def test_docs_no_legacy_project_and_link_kirana():
    """docs/demo-script.md and docs/architecture.md must not reference legacy project, and link Kirana."""
    demo_script_path = ROOT_DIR / "docs" / "demo-script.md"
    arch_path = ROOT_DIR / "docs" / "architecture.md"

    assert demo_script_path.exists()
    assert arch_path.exists()

    demo_text = demo_script_path.read_text(encoding="utf-8")
    arch_text = arch_path.read_text(encoding="utf-8")

    legacy_pattern_a = "green" + " grid"
    legacy_pattern_b = "green" + "grid"
    assert legacy_pattern_a not in demo_text.lower()
    assert legacy_pattern_b not in demo_text.lower()
    assert legacy_pattern_a not in arch_text.lower()
    assert legacy_pattern_b not in arch_text.lower()

    assert "KiranaCatalog" in arch_text or "catalog" in arch_text.lower()
    assert "DEMO-SCRIPT.md" in demo_text


def test_pitch_md_exists_and_word_count():
    """PITCH.md must exist, be <= 600 words, and cover problem, solution, Gnani models, and synthetic data."""
    pitch_path = ROOT_DIR / "PITCH.md"
    assert pitch_path.exists(), "PITCH.md must exist"

    content = pitch_path.read_text(encoding="utf-8")
    words = content.split()
    word_count = len(words)
    assert word_count <= 600, f"PITCH.md must be <= 600 words, found {word_count}"
    assert word_count >= 100, f"PITCH.md is too short: {word_count} words"

    assert "Prisma v2.5" in content
    assert "Timbre v3.0" in content
    assert "Shivani" in content
    assert "hi-IN" in content
    assert "hi-en" in content
    assert "synthetic" in content.lower()


def test_demo_script_structure_and_turns():
    """demo/DEMO-SCRIPT.md must exist, contain all 5 turns, timing markers, narration note, and fixture filenames."""
    script_path = ROOT_DIR / "demo" / "DEMO-SCRIPT.md"
    assert script_path.exists(), "demo/DEMO-SCRIPT.md must exist"

    content = script_path.read_text(encoding="utf-8")

    # 5 turn markers
    for turn_num in range(1, 6):
        assert f"Turn {turn_num}" in content, f"Missing Turn {turn_num} marker"

    # Timing beats
    assert "0:00" in content
    assert "0:30" in content
    assert "1:00" in content
    assert "1:40" in content
    assert "2:20" in content
    assert "2:45" in content

    # Canonical prompts / key items
    assert "Bhaiya, 2 kilo atta kitne ka hai?" in content
    assert "2 kilo atta aur 1 litre tel le lo, total kitna hua?" in content
    assert "Doodh hai kya stock mein?" in content
    assert "chai patti" in content.lower()
    assert "255" in content
    assert "190" in content

    # Audio fixtures
    assert "demo/turn_01_price.wav" in content
    assert "demo/turn_02_order_total.wav" in content
    assert "demo/turn_03_stock.wav" in content
    assert "demo/turn_04_second_order.wav" in content
    assert "demo/turn_05_closing.wav" in content

    # Narration track separation note
    assert "narration" in content.lower()

    # Submission duration requirement note (2-3 minute)
    assert "2–3 minute" in content or "2-3 minute" in content or "2 to 3 minute" in content.lower()


def test_env_example_gnani_key_is_empty():
    """.env.example must have an empty GNANI_API_KEY value."""
    env_example = ROOT_DIR / ".env.example"
    assert env_example.exists()

    content = env_example.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.startswith("GNANI_API_KEY")]
    assert len(lines) == 1, "Exactly one GNANI_API_KEY line required in .env.example"
    assert lines[0] == "GNANI_API_KEY=", "GNANI_API_KEY must have an empty value in .env.example"
