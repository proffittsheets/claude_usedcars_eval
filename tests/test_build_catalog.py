import json
import pytest
from pathlib import Path

from scripts.build_catalog import (
    slugify,
    best_nhtsa,
    best_fuel_economy,
    find_awd_carquery_trim,
    build_entry,
    get_images_for_model,
)


# --- slugify ---

def test_slugify_basic():
    assert slugify("Toyota RAV4 2024") == "toyota-rav4-2024"

def test_slugify_special_chars():
    assert slugify("Mercedes-Benz C-Class") == "mercedes-benz-c-class"

def test_slugify_extra_spaces():
    assert slugify("Lincoln  Navigator") == "lincoln-navigator"


# --- best_nhtsa ---

def test_best_nhtsa_picks_highest():
    records = [
        {"overall": 4, "front_crash": 4},
        {"overall": 5, "front_crash": 5},
        {"overall": 3, "front_crash": 3},
    ]
    result = best_nhtsa(records)
    assert result["overall"] == 5

def test_best_nhtsa_skips_unrated():
    records = [{"overall": None}, {"overall": None}]
    assert best_nhtsa(records) is None

def test_best_nhtsa_empty():
    assert best_nhtsa([]) is None


# --- best_fuel_economy ---

def test_best_fuel_economy_prefers_awd():
    records = [
        {"drive": "Front-Wheel Drive", "mpg_combined": 36},
        {"drive": "All Wheel Drive", "mpg_combined": 33},
    ]
    result = best_fuel_economy(records, prefer_awd=True)
    assert result["drive"] == "All Wheel Drive"

def test_best_fuel_economy_falls_back_to_first():
    records = [
        {"drive": "Front-Wheel Drive", "mpg_combined": 36},
        {"drive": "Rear-Wheel Drive", "mpg_combined": 30},
    ]
    result = best_fuel_economy(records, prefer_awd=True)
    assert result["drive"] == "Front-Wheel Drive"

def test_best_fuel_economy_empty():
    assert best_fuel_economy([]) is None


# --- find_awd_carquery_trim ---

def test_find_awd_carquery_trim():
    trims = [
        {"trim": "FWD Base", "has_awd": False},
        {"trim": "AWD XSE", "has_awd": True},
    ]
    result = find_awd_carquery_trim(trims)
    assert result["trim"] == "AWD XSE"

def test_find_awd_carquery_trim_none():
    trims = [{"trim": "FWD", "has_awd": False}]
    assert find_awd_carquery_trim(trims) is None

def test_find_awd_carquery_trim_empty():
    assert find_awd_carquery_trim([]) is None


# --- get_images_for_model ---

def test_get_images_prefers_manufacturer():
    manifest = {
        "manufacturer": [{"make": "Toyota", "model": "Sienna", "year": 2024, "local_path": "manufacturer/img.jpg"}],
        "wikimedia": [{"make": "Toyota", "model": "Sienna", "year": 2024, "local_path": "wikimedia/img.jpg"}],
    }
    result = get_images_for_model("Toyota", "Sienna", 2024, manifest)
    assert result["exterior"] == ["manufacturer/img.jpg"]

def test_get_images_falls_back_to_wikimedia():
    manifest = {
        "manufacturer": [],
        "wikimedia": [{"make": "Toyota", "model": "Sienna", "year": 2024, "local_path": "wikimedia/img.jpg"}],
    }
    result = get_images_for_model("Toyota", "Sienna", 2024, manifest)
    assert result["exterior"] == ["wikimedia/img.jpg"]

def test_get_images_returns_empty_when_none():
    result = get_images_for_model("Toyota", "Sienna", 2024, {})
    assert result == {"exterior": [], "interior": []}


# --- build_entry ---

MSRP_SEED = {"Toyota": {"Sienna": {"2024": 37485}}}
IIHS = {"Toyota": {"Sienna": {"2024": "Top Safety Pick"}}}
COLORS = {"Toyota": {"Sienna": ["Midnight Black", "Blueprint"]}}
DETAILS = {"Toyota": {"Sienna": {"cup_holders": 12, "heated_seats": "front only", "audio_system": "JBL 12-speaker"}}}

FE_RECORD = {
    "make": "Toyota", "model": "Sienna", "year": 2024,
    "drive": "All Wheel Drive",
    "is_hybrid": True,
    "mpg_city": 36, "mpg_highway": 36, "mpg_combined": 36,
    "fuel_type": "Regular Gasoline",
    "source_url": "https://fueleconomy.gov/feg/...",
}

NHTSA_RECORD = {
    "overall": 5, "front_crash": 5, "side_crash": 5, "rollover": 4,
    "source_url": "https://api.nhtsa.gov/...",
}

CQ_TRIM = {
    "trim": "XSE AWD", "body_type": "Minivan", "seats": 8, "has_awd": True, "msrp_usd": None,
}

IMAGES = {"exterior": ["manufacturer/toyota/sienna/2024/01.jpg"], "interior": []}


def test_build_entry_produces_valid_entry():
    entry = build_entry(
        "Toyota", "Sienna", 2024,
        FE_RECORD, NHTSA_RECORD, CQ_TRIM,
        MSRP_SEED, IIHS, COLORS, DETAILS, IMAGES,
    )
    assert entry is not None
    assert entry["make"] == "Toyota"
    assert entry["model"] == "Sienna"
    assert entry["year"] == 2024
    assert entry["has_awd"] is True
    assert entry["is_hybrid"] is True
    assert entry["msrp_usd"] == 37485
    assert entry["price_tier"] == "low"  # 37485 < 40000
    assert entry["body_type"] == "Minivan"
    assert entry["seats"] == 8
    assert entry["safety"]["nhtsa_overall"] == 5
    assert entry["safety"]["iihs_overall"] == "Top Safety Pick"
    assert entry["color_options"] == ["Midnight Black", "Blueprint"]
    assert entry["details"]["cup_holders"] == 12


def test_build_entry_returns_none_when_over_budget():
    high_msrp_seed = {"Toyota": {"Sienna": {"2024": 85000}}}
    entry = build_entry(
        "Toyota", "Sienna", 2024,
        FE_RECORD, NHTSA_RECORD, CQ_TRIM,
        high_msrp_seed, IIHS, COLORS, DETAILS, IMAGES,
    )
    assert entry is None


def test_build_entry_returns_none_when_no_msrp():
    no_msrp_seed = {"Toyota": {"Sienna": {}}}
    entry = build_entry(
        "Toyota", "Sienna", 2024,
        FE_RECORD, NHTSA_RECORD, CQ_TRIM,
        no_msrp_seed, IIHS, COLORS, DETAILS, IMAGES,
    )
    assert entry is None


def test_build_entry_handles_missing_nhtsa():
    entry = build_entry(
        "Toyota", "Sienna", 2024,
        FE_RECORD, None, CQ_TRIM,
        MSRP_SEED, IIHS, COLORS, DETAILS, IMAGES,
    )
    assert entry is not None
    assert entry["safety"]["nhtsa_overall"] is None
    assert entry["safety"]["iihs_overall"] == "Top Safety Pick"


def test_build_entry_price_tiers():
    low_seed = {"Toyota": {"Sienna": {"2024": 35000}}}
    med_seed = {"Toyota": {"Sienna": {"2024": 50000}}}
    high_seed = {"Toyota": {"Sienna": {"2024": 70000}}}

    assert build_entry("Toyota", "Sienna", 2024, FE_RECORD, None, CQ_TRIM, low_seed, IIHS, COLORS, DETAILS, IMAGES)["price_tier"] == "low"
    assert build_entry("Toyota", "Sienna", 2024, FE_RECORD, None, CQ_TRIM, med_seed, IIHS, COLORS, DETAILS, IMAGES)["price_tier"] == "medium"
    assert build_entry("Toyota", "Sienna", 2024, FE_RECORD, None, CQ_TRIM, high_seed, IIHS, COLORS, DETAILS, IMAGES)["price_tier"] == "high"
