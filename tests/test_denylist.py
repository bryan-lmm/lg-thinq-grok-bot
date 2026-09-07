"""Sanitization guard: banned marketing / household words must not appear."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "lg_thinq_specialty_cycles.egg-info",
    "src/thinq_specialty.egg-info",
    ".egg-info",
}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".json", ".txt", ".yml", ".yaml", ""}

# Substrings, case-insensitive. Keep this list aligned with the public denylist.
BANNED = [
    "haos",
    "hacs",
    "home assistant community store",
    "mojo",
    "hebron",
    "venmo",
    "cisco",
    "denim",
    "wrinkle care",
    "wrinklecare",
    "beachwear",
    "color care",
]


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.name == "test_denylist.py":
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "LICENSE",
            "NOTICE",
            ".gitignore",
            ".env.example",
        }:
            continue
        files.append(path)
    return files


def test_repo_has_no_denylist_terms():
    hits: list[str] = []
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lowered = text.lower()
        for term in BANNED:
            if term in lowered:
                hits.append(f"{path.relative_to(ROOT)}: {term}")
    assert hits == []
