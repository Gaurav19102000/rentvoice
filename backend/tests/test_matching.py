from app.database import SessionLocal
from app.matching import search_properties


def test_returns_top_three_within_budget_tolerance():
    db = SessionLocal()
    results, _ = search_properties(db, {"city": "Bangalore", "locality": "HSR", "budget_max": 35000, "bhk": 2})
    assert 0 < len(results) <= 3
    assert all(r.property.rent <= 35000 * 1.10 for r in results)
    assert results == sorted(results, key=lambda r: -r.score)


def test_relaxation_kicks_in_for_tight_budget():
    db = SessionLocal()
    results, note = search_properties(db, {"city": "Bengaluru", "locality": "MG Road", "budget_max": 15000, "bhk": 3})
    assert note != "" or not results


def test_unknown_city_returns_nothing():
    db = SessionLocal()
    results, note = search_properties(db, {"city": "Atlantis", "budget_max": 20000})
    assert results == [] and note == ""
