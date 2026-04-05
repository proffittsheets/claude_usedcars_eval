"""
Schema invariant tests for catalog.json.

These tests run against the actual processed catalog when it exists.
They enforce the hard contracts that the rest of the pipeline depends on.
"""
import json
import pytest
from pathlib import Path

CATALOG_PATH = Path(__file__).parent.parent / "data" / "processed" / "catalog.json"

REQUIRED_FIELDS = {"id", "make", "model", "year", "has_awd", "price_tier", "msrp_usd", "body_type"}
VALID_PRICE_TIERS = {"low", "medium", "high"}
VALID_MAKES = {"Toyota", "Nissan", "Mercedes-Benz", "Lincoln"}
MIN_YEAR = 2024
MAX_YEAR = 2026
MAX_MSRP = 80_000


@pytest.fixture(scope="module")
def catalog():
    if not CATALOG_PATH.exists():
        pytest.skip("catalog.json not yet generated — run build_catalog.py first")
    with open(CATALOG_PATH) as f:
        return json.load(f)


def test_catalog_is_nonempty(catalog):
    assert len(catalog) > 0, "Catalog must have at least one entry"


def test_all_required_fields_present(catalog):
    for entry in catalog:
        missing = REQUIRED_FIELDS - set(entry.keys())
        assert not missing, f"Entry {entry.get('id')} missing fields: {missing}"


def test_all_entries_have_awd(catalog):
    for entry in catalog:
        assert entry["has_awd"] is True, f"Entry {entry['id']} missing has_awd=True"


def test_all_years_in_range(catalog):
    for entry in catalog:
        assert MIN_YEAR <= entry["year"] <= MAX_YEAR, (
            f"Entry {entry['id']} year {entry['year']} out of range"
        )


def test_all_msrp_within_budget(catalog):
    for entry in catalog:
        assert entry["msrp_usd"] <= MAX_MSRP, (
            f"Entry {entry['id']} MSRP ${entry['msrp_usd']} exceeds max ${MAX_MSRP}"
        )


def test_all_price_tiers_valid(catalog):
    for entry in catalog:
        assert entry["price_tier"] in VALID_PRICE_TIERS, (
            f"Entry {entry['id']} has invalid tier '{entry['price_tier']}'"
        )


def test_price_tier_matches_msrp(catalog):
    for entry in catalog:
        msrp = entry["msrp_usd"]
        tier = entry["price_tier"]
        if msrp < 40_000:
            assert tier == "low", f"Entry {entry['id']} MSRP {msrp} should be 'low', got '{tier}'"
        elif msrp < 60_000:
            assert tier == "medium", f"Entry {entry['id']} MSRP {msrp} should be 'medium', got '{tier}'"
        else:
            assert tier == "high", f"Entry {entry['id']} MSRP {msrp} should be 'high', got '{tier}'"


def test_all_makes_valid(catalog):
    for entry in catalog:
        assert entry["make"] in VALID_MAKES, (
            f"Entry {entry['id']} has unexpected make '{entry['make']}'"
        )


def test_all_ids_unique(catalog):
    ids = [e["id"] for e in catalog]
    assert len(ids) == len(set(ids)), "Duplicate IDs found in catalog"


def test_safety_structure(catalog):
    for entry in catalog:
        safety = entry.get("safety", {})
        assert isinstance(safety, dict), f"Entry {entry['id']} safety is not a dict"
        # NHTSA ratings must be 1-5 or None
        for field in ("nhtsa_overall", "nhtsa_front_crash", "nhtsa_side_crash", "nhtsa_rollover"):
            val = safety.get(field)
            assert val is None or (isinstance(val, int) and 1 <= val <= 5), (
                f"Entry {entry['id']} {field}={val} is not 1-5 or None"
            )


def test_images_structure(catalog):
    for entry in catalog:
        images = entry.get("images", {})
        assert isinstance(images, dict), f"Entry {entry['id']} images is not a dict"
        assert "exterior" in images, f"Entry {entry['id']} missing images.exterior"
        assert "interior" in images, f"Entry {entry['id']} missing images.interior"
        assert isinstance(images["exterior"], list)
        assert isinstance(images["interior"], list)
