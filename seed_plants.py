"""Seed twelve demo plant listings across three demo nurseries.

Run with ``python seed_plants.py`` to add or refresh the listings, or
``python seed_plants.py --reset`` to remove only this script's listings.
"""
import argparse
import sys
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.models  # noqa: F401 - register ORM relationships
from app.database import SessionLocal
from app.models import (
    CartItem,
    Nursery,
    OrderItem,
    Plant,
    PlantRentalOrder,
    PurchaseOrder,
    RentalOrder,
)

SEED_MARKER = "#greennest-seed-plants-v1"
SEED_NURSERY_MARKER = "#greennest-seed-nursery-v1"
NURSERY_NAMES = ("Green Oasis Nursery", "Flora Haven", "Urban Jungle")

PLANTS: list[dict[str, Any]] = [
    {
        "name": "Monstera Deliciosa",
        "category": "Indoor",
        "size": "Large",
        "description": "A statement tropical plant with distinctive split leaves. Rent: ৳90/day; 30-day estimate: ৳2,700.",
        "care_instructions": "Bright, indirect light. Water when the top 2–3 cm of soil is dry; provide a moss pole as it grows.",
        "buy_price": Decimal("4200.00"),
        "rent_price": Decimal("90.00"),
        "available_quantity": 8,
        "image_url": "https://images.unsplash.com/photo-1617173944883-6ffbd35d584d?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Snake Plant Laurentii",
        "category": "Indoor",
        "size": "Medium",
        "description": "A resilient upright houseplant with golden-edged leaves. Rent: ৳45/day; 30-day estimate: ৳1,350.",
        "care_instructions": "Tolerates low to bright indirect light. Let the soil dry fully between waterings.",
        "buy_price": Decimal("1850.00"),
        "rent_price": Decimal("45.00"),
        "available_quantity": 14,
        "image_url": "https://images.unsplash.com/photo-1509423350716-97f9360b4e09?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Areca Palm",
        "category": "Indoor",
        "size": "Large",
        "description": "A graceful, feathery palm for bright living spaces. Rent: ৳110/day; 30-day estimate: ৳3,300.",
        "care_instructions": "Place in bright, filtered light. Keep soil lightly moist, not waterlogged, and mist in dry weather.",
        "buy_price": Decimal("5600.00"),
        "rent_price": Decimal("110.00"),
        "available_quantity": 6,
        "image_url": "https://images.unsplash.com/photo-1497250681960-ef046c08a56e?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Garden Croton",
        "category": "Outdoor",
        "size": "Medium",
        "description": "Colorful foliage that brings a warm accent to patios and gardens. Rent: ৳55/day; 30-day estimate: ৳1,650.",
        "care_instructions": "Give bright light and several hours of gentle sun for vivid color. Water when the top layer of soil dries.",
        "buy_price": Decimal("2100.00"),
        "rent_price": Decimal("55.00"),
        "available_quantity": 10,
        "image_url": "https://images.unsplash.com/photo-1596547609652-9cf5d8d76921?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Bougainvillea",
        "category": "Outdoor",
        "size": "Large",
        "description": "A sun-loving flowering climber with vivid papery bracts. Rent: ৳75/day; 30-day estimate: ৳2,250.",
        "care_instructions": "Grow in full sun with well-draining soil. Water deeply, then allow the soil to dry slightly.",
        "buy_price": Decimal("3200.00"),
        "rent_price": Decimal("75.00"),
        "available_quantity": 7,
        "image_url": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Echeveria Elegans",
        "category": "Succulents",
        "size": "Small",
        "description": "A compact, pale-green rosette succulent for sunny desks and shelves. Rent: ৳18/day; 30-day estimate: ৳540.",
        "care_instructions": "Provide several hours of bright light. Use a gritty mix and water only after the soil dries completely.",
        "buy_price": Decimal("650.00"),
        "rent_price": Decimal("18.00"),
        "available_quantity": 24,
        "image_url": "https://images.unsplash.com/photo-1459156212016-c812468e2115?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Golden Barrel Cactus",
        "category": "Succulents",
        "size": "Small",
        "description": "A sculptural, slow-growing cactus with a sunny golden form. Rent: ৳20/day; 30-day estimate: ৳600.",
        "care_instructions": "Place in strong light. Use a cactus mix and water sparingly, allowing the pot to dry between waterings.",
        "buy_price": Decimal("950.00"),
        "rent_price": Decimal("20.00"),
        "available_quantity": 18,
        "image_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Jade Plant",
        "category": "Succulents",
        "size": "Medium",
        "description": "A branching, easy-care succulent with glossy oval leaves. Rent: ৳30/day; 30-day estimate: ৳900.",
        "care_instructions": "Give bright light and a well-draining pot. Water thoroughly only after the soil has dried.",
        "buy_price": Decimal("1250.00"),
        "rent_price": Decimal("30.00"),
        "available_quantity": 12,
        "image_url": "https://images.unsplash.com/photo-1508595165502-3e2652e5a405?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Peace Lily",
        "category": "Flowery",
        "size": "Medium",
        "description": "Elegant white blooms and deep-green foliage for calm indoor spaces. Rent: ৳60/day; 30-day estimate: ৳1,800.",
        "care_instructions": "Keep in medium, indirect light. Water when the surface begins to dry; avoid direct afternoon sun.",
        "buy_price": Decimal("2400.00"),
        "rent_price": Decimal("60.00"),
        "available_quantity": 9,
        "image_url": "https://images.unsplash.com/photo-1563241527-3004b7be0ffd?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Anthurium Red",
        "category": "Flowery",
        "size": "Medium",
        "description": "A tropical favorite with glossy leaves and long-lasting red spathes. Rent: ৳70/day; 30-day estimate: ৳2,100.",
        "care_instructions": "Bright, indirect light and evenly moist, airy soil. Keep away from cold drafts and harsh sunlight.",
        "buy_price": Decimal("2850.00"),
        "rent_price": Decimal("70.00"),
        "available_quantity": 8,
        "image_url": "https://images.unsplash.com/photo-1592150621744-aca64f48394a?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Philodendron Pink Princess",
        "category": "Rare plants",
        "size": "Medium",
        "description": "A sought-after climbing philodendron with pink-variegated leaves. Rent: ৳140/day; 30-day estimate: ৳4,200.",
        "care_instructions": "Provide bright, indirect light to support variegation. Use a chunky mix and water when the top layer dries.",
        "buy_price": Decimal("7800.00"),
        "rent_price": Decimal("140.00"),
        "available_quantity": 3,
        "image_url": "https://images.unsplash.com/photo-1604762524889-3e2fcc145683?auto=format&fit=crop&w=600&q=80",
    },
    {
        "name": "Alocasia Dragon Scale",
        "category": "Rare plants",
        "size": "Small",
        "description": "A collector's alocasia with dramatic, textured silvery-green leaves. Rent: ৳125/day; 30-day estimate: ৳3,750.",
        "care_instructions": "Use warm, humid conditions and bright indirect light. Keep the mix lightly moist while avoiding standing water.",
        "buy_price": Decimal("6900.00"),
        "rent_price": Decimal("125.00"),
        "available_quantity": 4,
        "image_url": "https://images.unsplash.com/photo-1614594975525-e45190c55d0b?auto=format&fit=crop&w=600&q=80",
    },
]

DEPENDENT_MODELS = (
    CartItem,
    PurchaseOrder,
    OrderItem,
    RentalOrder,
    PlantRentalOrder,
)


def reset_seeded_plants(db: Session) -> tuple[int, int]:
    """Delete this script's listings only; refuse if orders or carts reference them."""
    seeded_plants = db.scalars(
        select(Plant).where(Plant.image_url.endswith(SEED_MARKER))
    ).all()
    if seeded_plants:
        plant_ids = [plant.id for plant in seeded_plants]
        for model in DEPENDENT_MODELS:
            reference = db.scalar(
                select(model.plant_id)
                .where(model.plant_id.in_(plant_ids))
                .limit(1)
            )
            if reference is not None:
                raise RuntimeError(
                    "Reset stopped: at least one seeded plant is referenced by "
                    f"{model.__tablename__}. No seeded plants were deleted."
                )

    for plant in seeded_plants:
        db.delete(plant)

    db.flush()
    seeded_nurseries = db.scalars(
        select(Nursery).where(Nursery.description.like(f"%{SEED_NURSERY_MARKER}%"))
    ).all()
    removed_nurseries = 0
    for nursery in seeded_nurseries:
        has_listings = db.scalar(
            select(Plant.id).where(Plant.nursery_id == nursery.id).limit(1)
        )
        if has_listings is None:
            db.delete(nursery)
            removed_nurseries += 1

    db.commit()
    return len(seeded_plants), removed_nurseries


def choose_nursery_owner(db: Session, existing_seeded: list[Plant]) -> Nursery:
    if existing_seeded:
        nursery_ids = {plant.nursery_id for plant in existing_seeded}
        nurseries = db.scalars(
            select(Nursery).where(Nursery.id.in_(nursery_ids))
        ).all()
        if len(nurseries) != len(nursery_ids):
            raise RuntimeError("A nursery for existing seeded plants no longer exists.")
        owner_ids = {nursery.owner_id for nursery in nurseries}
        if len(owner_ids) != 1:
            raise RuntimeError(
                "Seeded plants belong to multiple nursery owners; refusing to "
                "change their assignments."
            )
        return nurseries[0]

    nurseries = db.scalars(
        select(Nursery)
        .where(Nursery.status == "active")
        .order_by(Nursery.id)
    ).all()
    if not nurseries:
        raise RuntimeError(
            "No active nursery exists. Activate or create a nursery before seeding plants."
        )
    return nurseries[0]


def get_seed_nurseries(db: Session, owner_nursery: Nursery) -> list[Nursery]:
    existing = db.scalars(
        select(Nursery).where(
            Nursery.owner_id == owner_nursery.owner_id,
            Nursery.name.in_(NURSERY_NAMES),
        )
    ).all()
    nurseries_by_name = {nursery.name: nursery for nursery in existing}

    for name in NURSERY_NAMES:
        nursery = nurseries_by_name.get(name)
        if nursery is not None:
            if not (nursery.description or "").startswith(SEED_NURSERY_MARKER):
                raise RuntimeError(
                    f"Nursery {name!r} already exists and is not owned by this "
                    "seed script; refusing to modify it."
                )
            if nursery.status != "active":
                raise RuntimeError(
                    f"Seed nursery {name!r} is not active; refusing to reactivate it."
                )
            continue

        nursery = Nursery(
            owner_id=owner_nursery.owner_id,
            name=name,
            description=(
                f"{SEED_NURSERY_MARKER} Demo nursery for GreenNest seed listings."
            ),
            address=owner_nursery.address,
            city=owner_nursery.city,
            phone=owner_nursery.phone,
            email=owner_nursery.email,
            image_url=owner_nursery.image_url,
            status="active",
        )
        db.add(nursery)
        nurseries_by_name[name] = nursery

    db.flush()
    return [nurseries_by_name[name] for name in NURSERY_NAMES]


def seed_plants(db: Session) -> tuple[int, int, int]:
    existing_seeded = db.scalars(
        select(Plant).where(Plant.image_url.endswith(SEED_MARKER))
    ).all()
    existing_ids = [plant.id for plant in existing_seeded]
    referenced_ids: set[int] = set()
    for model in DEPENDENT_MODELS:
        referenced_ids.update(
            db.scalars(
                select(model.plant_id).where(model.plant_id.in_(existing_ids))
            ).all()
        )

    owner_nursery = choose_nursery_owner(db, existing_seeded)
    nurseries = get_seed_nurseries(db, owner_nursery)
    seeded_by_name = {plant.name: plant for plant in existing_seeded}
    added = 0
    updated = 0
    preserved = 0
    messages: list[str] = []
    for index, data in enumerate(PLANTS):
        nursery = nurseries[index % len(nurseries)]
        plant = seeded_by_name.get(data["name"])
        values = {
            **data,
            "availability_status": "available_for_both",
            "image_url": f"{data['image_url']}{SEED_MARKER}",
        }
        if plant is not None and plant.id in referenced_ids:
            plant.image_url = values["image_url"]
            preserved += 1
            messages.append(
                f"Preserved cart/order details: {data['name']} "
                f"(nursery: {plant.nursery.name})"
            )
            continue

        collision_statement = select(Plant.id).where(
            Plant.nursery_id == nursery.id,
            Plant.name == data["name"],
        )
        if plant is not None:
            collision_statement = collision_statement.where(Plant.id != plant.id)
        collision = db.scalar(collision_statement.limit(1))
        if collision is not None:
            raise RuntimeError(
                f"Plant name {data['name']!r} already exists in nursery "
                f"{nursery.id}; refusing to overwrite an unseeded listing."
            )

        if plant is None:
            plant = Plant(nursery_id=nursery.id, **values)
            db.add(plant)
            added += 1
            action = "Added"
        else:
            plant.nursery_id = nursery.id
            for key, value in values.items():
                setattr(plant, key, value)
            updated += 1
            action = "Updated"
        messages.append(
            f"{action} plant: {data['name']} — {nursery.name}"
        )

    db.commit()
    for message in messages:
        print(message)
    return added, updated, preserved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="remove only listings created by this script",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset:
            removed, removed_nurseries = reset_seeded_plants(db)
            print(
                f"Reset complete: removed {removed} seeded plant listing(s) "
                f"and {removed_nurseries} unused seed nursery profile(s)."
            )
        else:
            added, updated, preserved = seed_plants(db)
            if added or updated or preserved:
                print(
                    f"Seed complete: added {added}, refreshed {updated}, and "
                    f"preserved {preserved} referenced listing(s)."
                )
            else:
                print("Seed complete: all 12 plant listings are current.")
        return 0
    except (RuntimeError, SQLAlchemyError) as exc:
        db.rollback()
        print(f"Plant seeding failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
