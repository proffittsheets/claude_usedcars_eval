import json
import responses as responses_lib
import pytest

from scripts.fetch_carquery_specs import (
    fetch_trims,
    has_awd,
    normalize_body_type,
    normalize_trim,
    fetch_for_model,
)
from scripts.config import CARQUERY_BASE
from scripts.utils import strip_jsonp


# --- strip_jsonp ---

def test_strip_jsonp_basic():
    payload = {"Trims": [{"model_id": "1"}]}
    jsonp = f"?({json.dumps(payload)});"
    result = strip_jsonp(jsonp)
    assert result == payload


def test_strip_jsonp_with_callback_name():
    payload = {"Trims": []}
    jsonp = f"jQuery123({json.dumps(payload)});"
    result = strip_jsonp(jsonp)
    assert result == payload


# --- has_awd ---

@pytest.mark.parametrize("drive,expected", [
    ("AWD", True),
    ("4WD", True),
    ("All Wheel Drive", True),
    ("all-wheel drive", True),
    ("FWD", False),
    ("RWD", False),
    ("", False),
    (None, False),
])
def test_has_awd(drive, expected):
    assert has_awd(drive) == expected


# --- normalize_body_type ---

@pytest.mark.parametrize("body,expected", [
    ("Minivan", "Minivan"),
    ("Sport Utility Vehicle", "SUV"),
    ("Crossover", "SUV"),
    ("Sedan", "Sedan"),
    ("Saloon", "Sedan"),
    ("", None),
    (None, None),
])
def test_normalize_body_type(body, expected):
    assert normalize_body_type(body) == expected


# --- normalize_trim ---

def test_normalize_trim(sample_carquery_response):
    raw_data = strip_jsonp(sample_carquery_response)
    raw_trim = raw_data["Trims"][0]
    result = normalize_trim(raw_trim)
    assert result["model"] == "Sienna"
    assert result["year"] == "2024"
    assert result["body_type"] == "Minivan"
    assert result["has_awd"] is True
    assert result["seats"] == 8
    assert result["msrp_usd"] == 40000
    assert result["sold_in_us"] is True


def test_normalize_trim_handles_missing_msrp():
    raw = {"model_id": "1", "model_name": "Test", "model_msrp": None, "model_drive": "FWD"}
    result = normalize_trim(raw)
    assert result["msrp_usd"] is None


def test_normalize_trim_handles_invalid_msrp():
    raw = {"model_id": "1", "model_name": "Test", "model_msrp": "N/A", "model_drive": "FWD"}
    result = normalize_trim(raw)
    assert result["msrp_usd"] is None


# --- fetch_trims ---

@responses_lib.activate
def test_fetch_trims_returns_list(sample_carquery_response):
    responses_lib.add(
        responses_lib.GET,
        CARQUERY_BASE,
        body=sample_carquery_response,
    )
    result = fetch_trims("Toyota", "Sienna", 2024)
    assert len(result) == 1
    assert result[0]["model_name"] == "Sienna"


@responses_lib.activate
def test_fetch_trims_returns_empty_on_error():
    responses_lib.add(
        responses_lib.GET,
        CARQUERY_BASE,
        status=500,
    )
    result = fetch_trims("Toyota", "Nonexistent", 2024)
    assert result == []


@responses_lib.activate
def test_fetch_for_model_returns_normalized(sample_carquery_response):
    responses_lib.add(
        responses_lib.GET,
        CARQUERY_BASE,
        body=sample_carquery_response,
    )
    result = fetch_for_model("Toyota", "Sienna", 2024)
    assert len(result) == 1
    assert result[0]["has_awd"] is True
    assert result[0]["body_type"] == "Minivan"


@responses_lib.activate
def test_fetch_for_model_returns_empty_when_no_trims():
    empty = "?({\"Trims\": []});"
    responses_lib.add(
        responses_lib.GET,
        CARQUERY_BASE,
        body=empty,
    )
    result = fetch_for_model("Toyota", "Nonexistent", 2024)
    assert result == []
