import re
from pathlib import Path

from app.core.constants import MENU_PAGES


def test_seeded_menu_urls_match_frontend_routes():
    project_root = Path(__file__).resolve().parents[2]
    layout_source = (project_root / "frontend" / "js" / "layout.js").read_text(
        encoding="utf-8"
    )
    frontend_routes = [
        (label, url)
        for url, label in re.findall(
            r'\{\s*url:\s*"([^"]+)",\s*label:\s*"([^"]+)"',
            layout_source,
        )
    ]
    expected_routes = [
        ("Dashboard", "/dashboard"),
        ("Buy Plants", "/buy"),
        ("Rent Plants", "/rent"),
        ("Maintenance", "/maintenance"),
        ("My Profile", "/profile"),
    ]

    assert frontend_routes == expected_routes
    assert [(name, url) for name, url, _ in MENU_PAGES] == expected_routes


def test_dashboard_and_profile_use_shared_layout():
    project_root = Path(__file__).resolve().parents[2]

    for page in ("dashboard.html", "profile.html"):
        page_source = (project_root / "frontend" / page).read_text(
            encoding="utf-8"
        )
        assert 'data-layout="dashboard"' in page_source
        assert '<aside class="sidebar" id="sidebar"></aside>' in page_source
