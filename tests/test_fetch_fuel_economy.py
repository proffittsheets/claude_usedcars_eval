import responses as responses_lib
import pytest

from scripts.fetch_fuel_economy import (
    _parse_menu_items,
    _parse_vehicle_record,
    get_api_model_names,
    fetch_vehicle_ids,
    fetch_vehicle_record,
    is_hybrid,
    normalize_record,
    fetch_for_model,
)
from scripts.config import FUEL_ECONOMY_BASE


# --- XML parsing ---

def test_parse_menu_items(sample_fuel_economy_model_xml):
    items = _parse_menu_items(sample_fuel_economy_model_xml)
    assert len(items) == 3
    assert items[0] == {"text": "Sienna AWD", "value": "Sienna AWD"}


def test_parse_menu_items_empty():
    xml = '<?xml version="1.0"?><menuItems></menuItems>'
    assert _parse_menu_items(xml) == []


def test_parse_menu_items_invalid_xml():
    assert _parse_menu_items("not xml at all") == []


def test_parse_vehicle_record(sample_fuel_economy_record_xml):
    record = _parse_vehicle_record(sample_fuel_economy_record_xml)
    assert record["id"] == "48751"
    assert record["make"] == "Toyota"
    assert record["atvType"] == "Hybrid"


def test_parse_vehicle_record_invalid_xml():
    assert _parse_vehicle_record("bad xml") is None


# --- get_api_model_names ---

@responses_lib.activate
def test_get_api_model_names_prefix_match(sample_fuel_economy_model_xml):
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/menu/model",
        body=sample_fuel_economy_model_xml,
    )
    result = get_api_model_names("Toyota", "Sienna", 2024)
    assert "Sienna AWD" in result
    assert "Sienna FWD" in result
    assert "RAV4" not in result  # doesn't match "Sienna" prefix


@responses_lib.activate
def test_get_api_model_names_returns_empty_on_error():
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/menu/model",
        status=500,
    )
    result = get_api_model_names("Toyota", "Sienna", 2024)
    assert result == []


# --- fetch_vehicle_ids ---

@responses_lib.activate
def test_fetch_vehicle_ids(sample_fuel_economy_options_xml):
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/menu/options",
        body=sample_fuel_economy_options_xml,
    )
    result = fetch_vehicle_ids("Toyota", "Sienna AWD", 2024)
    assert len(result) == 2
    assert result[0]["value"] == "48751"


@responses_lib.activate
def test_fetch_vehicle_ids_returns_empty_on_error():
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/menu/options",
        status=404,
    )
    result = fetch_vehicle_ids("Toyota", "Nonexistent", 2024)
    assert result == []


# --- fetch_vehicle_record ---

@responses_lib.activate
def test_fetch_vehicle_record(sample_fuel_economy_record_xml):
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/48751",
        body=sample_fuel_economy_record_xml,
    )
    result = fetch_vehicle_record("48751")
    assert result["id"] == "48751"
    assert result["make"] == "Toyota"


@responses_lib.activate
def test_fetch_vehicle_record_returns_none_on_error():
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/99999",
        status=500,
    )
    result = fetch_vehicle_record("99999")
    assert result is None


# --- is_hybrid ---

def test_is_hybrid_detects_hybrid():
    assert is_hybrid({"atvType": "Hybrid", "fuelType1": "Regular Gasoline"}) is True


def test_is_hybrid_detects_phev():
    assert is_hybrid({"atvType": "Plug-in Hybrid/Electric", "fuelType1": "Regular Gasoline"}) is True


def test_is_hybrid_detects_non_hybrid():
    assert is_hybrid({"atvType": "", "fuelType1": "Regular Gasoline"}) is False


# --- normalize_record ---

def test_normalize_record(sample_fuel_economy_record_xml):
    raw = _parse_vehicle_record(sample_fuel_economy_record_xml)
    result = normalize_record(raw)
    assert result["make"] == "Toyota"
    assert result["model"] == "Sienna"
    assert result["mpg_combined"] == 36
    assert result["is_hybrid"] is True
    assert result["vehicle_id"] == "48751"
    assert "source_url" in result


# --- fetch_for_model ---

@responses_lib.activate
def test_fetch_for_model_full_flow(
    sample_fuel_economy_model_xml,
    sample_fuel_economy_options_xml,
    sample_fuel_economy_record_xml,
):
    # Step 1: model list
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/menu/model",
        body=sample_fuel_economy_model_xml,
    )
    # Step 2: options for "Sienna AWD"
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/menu/options",
        body=sample_fuel_economy_options_xml,
    )
    # Step 2: options for "Sienna FWD" (empty)
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/menu/options",
        body='<?xml version="1.0"?><menuItems></menuItems>',
    )
    # Step 3: vehicle records for IDs 48751 and 48752
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/48751",
        body=sample_fuel_economy_record_xml,
    )
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/48752",
        body=sample_fuel_economy_record_xml,
    )

    results = fetch_for_model("Toyota", "Sienna", 2024)
    assert len(results) == 2
    assert all(r["is_hybrid"] for r in results)


@responses_lib.activate
def test_fetch_for_model_returns_empty_when_no_model_names():
    responses_lib.add(
        responses_lib.GET,
        f"{FUEL_ECONOMY_BASE}/vehicle/menu/model",
        body='<?xml version="1.0"?><menuItems></menuItems>',
    )
    results = fetch_for_model("Toyota", "Nonexistent", 2024)
    assert results == []
