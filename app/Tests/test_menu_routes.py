import re
from pathlib import Path

from sqlalchemy import select

from app.core.constants import MENU_PAGES, NURSERY_MENU_PAGES
from app.models import Page, Role, RolePage
from app.seed import seed_initial_data


def _frontend_routes(layout_source: str, role: str) -> list[tuple[str, str, str]]:
    match = re.search(rf"{role}: \[(.*?)\]", layout_source, re.DOTALL)
    assert match is not None
    return re.findall(
        r'\{\s*url:\s*"([^"]+)",\s*label:\s*"([^"]+)",\s*file:\s*"([^"]+)"',
        match.group(1),
    )


def test_seeded_menus_match_role_specific_frontend_routes():
    project_root = Path(__file__).resolve().parents[2]
    layout_source = (project_root / "frontend" / "js" / "layout.js").read_text(
        encoding="utf-8"
    )
    expected_customer = [
        ("/dashboard", "Dashboard", "dashboard.html"),
        ("/buy", "Buy", "buy.html"),
        ("/rent", "Rent", "rent.html"),
        ("/customer-history", "Purchase History", "customer-history.html"),
        ("/maintenance", "Maintenance", "maintenance.html"),
        ("/profile", "Profile", "profile.html"),
    ]
    expected_nursery = [
        ("/nursery-dashboard", "Nursery Dashboard", "nursery-dashboard.html"),
        ("/my-plants", "My Plants", "my-plants.html"),
        ("/add-plant", "Add Plant", "add-plant.html"),
        ("/sell-orders", "Sell Orders", "sell-orders.html"),
        ("/rent-orders", "Rent Orders", "rent-orders.html"),
        ("/nursery-maintenance", "Nursery Maintenance", "nursery-maintainance.html"),
        ("/nursery-profile", "Nursery Profile", "nursery-profile.html"),
    ]

    assert _frontend_routes(layout_source, "User") == expected_customer
    assert _frontend_routes(layout_source, "Nursery") == expected_nursery
    assert [(url, name) for name, url, _ in MENU_PAGES] == [
        (url, name) for url, name, _ in expected_customer
    ]
    assert [(url, name) for name, url, _ in NURSERY_MENU_PAGES] == [
        (url, name) for url, name, _ in expected_nursery
    ]


def test_menu_seed_assigns_pages_only_to_the_matching_role(db_session):
    seed_initial_data(db_session)

    role_ids = dict(
        db_session.execute(select(Role.role_name, Role.id)).all()
    )
    assigned_pages = {
        role_name: set(
            db_session.scalars(
                select(Page.page_url)
                .join(RolePage, RolePage.page_id == Page.id)
                .where(RolePage.role_id == role_ids[role_name])
            ).all()
        )
        for role_name in role_ids
    }

    assert assigned_pages["User"] == {url for _, url, _ in MENU_PAGES}
    assert assigned_pages["Nursery"] == {url for _, url, _ in NURSERY_MENU_PAGES}
    assert assigned_pages["Admin"] == set()


def test_every_portal_page_uses_the_shared_role_guard():
    project_root = Path(__file__).resolve().parents[2]
    customer_pages = (
        "dashboard.html",
        "dashboard-template.html",
        "buy.html",
        "rent.html",
        "customer-history.html",
        "maintenance.html",
        "profile.html",
        "plants.html",
        "about.html",
        "contact.html",
    )
    nursery_pages = (
        "nursery-dashboard.html",
        "my-plants.html",
        "add-plant.html",
        "sell-orders.html",
        "rent-orders.html",
        "nursery-maintainance.html",
        "nursery-profile.html",
    )

    for page in customer_pages:
        source = (project_root / "frontend" / page).read_text(encoding="utf-8")
        assert 'data-layout="dashboard"' in source
        assert 'src="js/layout.js"' in source

    for page in nursery_pages:
        source = (project_root / "frontend" / page).read_text(encoding="utf-8")
        assert 'data-layout="nursery"' in source
        assert 'src="js/layout.js"' in source
