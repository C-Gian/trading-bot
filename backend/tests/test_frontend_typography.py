from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_frontend_uses_the_local_system_ui_stack_without_font_networks() -> None:
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend/src/style.css").read_text(encoding="utf-8")

    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
    assert "@font-face" not in css
    assert (
        'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI Variable", '
        '"Segoe UI", Roboto, Helvetica, Arial, sans-serif'
    ) in css
    assert "Instrument Serif" not in css
    assert "Figtree" not in css


def test_dashboard_and_research_lab_share_the_global_type_system() -> None:
    css = (ROOT / "frontend/src/style.css").read_text(encoding="utf-8")
    assert "body {\n  font-family: var(--sans);" in css
    assert ".research-candidate-title h3" in css
    assert ".verdict" in css
    assert "var(--serif)" not in css
