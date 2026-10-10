import re
from pathlib import Path

from app.core.constants import MENU_PAGES


def test_seeded_menu_urls_match_frontend_routes():
    project_root = Path(__file__).resolve().parents[2]
    layout_source = (project_root / "frontend" / "js" / "layout.js").read_text(
        encoding="utf-8"
    )
    frontend_routes = {
        label: url
        for url, label in re.findall(
            r'\{\s*url:\s*"([^"]+)",\s*label:\s*"([^"]+)"',
            layout_source,
        )
    }

    assert {name: url for name, url, _ in MENU_PAGES} == frontend_routes
