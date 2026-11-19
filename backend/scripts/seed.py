"""Seed ~90 realistic Bengaluru listings. Run: python -m scripts.seed"""
import random
from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app.geo import LOCALITIES
from app.models import Property, utcnow

random.seed(42)

BASE_RENT = {  # rough 2BHK rent per locality (INR / month)
    "Koramangala": 38000, "Indiranagar": 42000, "HSR Layout": 32000, "Whitefield": 28000,
    "Electronic City": 18000, "Marathahalli": 25000, "BTM Layout": 24000, "Jayanagar": 30000,
    "JP Nagar": 26000, "Bellandur": 30000, "Hebbal": 29000, "Yelahanka": 20000,
    "Malleshwaram": 31000, "Banashankari": 22000, "Sarjapur Road": 27000, "MG Road": 48000,
}
AMENITIES = ["parking", "lift", "power backup", "gym", "swimming pool", "security", "wifi", "balcony"]
TYPES = ["apartment"] * 6 + ["independent_house"] * 2 + ["villa", "pg", "studio"]
OWNERS = ["Ramesh Kumar", "Priya Nair", "Suresh Reddy", "Anita Rao", "Vikram Shetty", "Meena Iyer",
          "Arjun Gowda", "Lakshmi Prasad", "Farhan Ali", "Deepa Menon", "Karthik S", "Neha Jain"]
BHK_FACTOR = {0: 0.45, 1: 0.65, 2: 1.0, 3: 1.4, 4: 1.9}


def make(locality: str, centre: tuple[float, float]) -> Property:
    ptype = random.choice(TYPES)
    bhk = 0 if ptype in {"pg", "studio"} else random.choice([1, 2, 2, 2, 3, 3, 4] if ptype == "villa" else [1, 2, 2, 3])
    if ptype == "villa":
        bhk = max(bhk, 3)
    rent = int(BASE_RENT[locality] * BHK_FACTOR[bhk] * random.uniform(0.85, 1.2) * (1.5 if ptype == "villa" else 1))
    rent = round(rent / 500) * 500
    furnishing = random.choice(["unfurnished", "semi", "semi", "fully"])
    label = "Studio" if ptype == "studio" else "PG room" if ptype == "pg" else f"{bhk} BHK {ptype.replace('_', ' ')}"
    return Property(
        title=f"{label} in {locality}",
        city="bengaluru",
        locality=locality,
        address=f"{random.randint(1, 40)}th Cross, {locality}",
        lat=centre[0] + random.uniform(-0.02, 0.02),
        lng=centre[1] + random.uniform(-0.02, 0.02),
        rent=rent,
        deposit=rent * random.choice([2, 3, 5, 6]),
        bhk=bhk,
        property_type=ptype,
        furnishing=furnishing,
        area_sqft=int((350 if bhk == 0 else 550 * bhk) * random.uniform(0.9, 1.3)),
        amenities=random.sample(AMENITIES, k=random.randint(2, 5)),
        pets_allowed=random.random() < 0.35,
        available_from=date.today() + timedelta(days=random.randint(0, 45)),
        description=random.choice([
            "Well-ventilated, east-facing, close to the main road.",
            "Quiet lane, good water supply, 5 minutes to the metro.",
            "Gated society with a children's play area.",
            "Newly painted, modular kitchen, covered parking.",
            "Walking distance to supermarkets and cafes.",
        ]),
        owner_name=random.choice(OWNERS),
        owner_phone=f"+9198{random.randint(10000000, 99999999)}",
        # ~10% stale listings to demonstrate auto-expiry
        last_verified_at=utcnow() - timedelta(days=random.choice([1, 3, 7, 12, 20, 45]) if random.random() < 0.9 else 60),
    )


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Property).delete()
    for locality, centre in LOCALITIES["bengaluru"].items():
        for _ in range(6):
            db.add(make(locality, centre))
    db.commit()
    print(f"Seeded {db.query(Property).count()} properties")
    db.close()


if __name__ == "__main__":
    main()
