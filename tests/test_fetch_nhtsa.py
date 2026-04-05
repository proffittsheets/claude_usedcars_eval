import responses as responses_lib
import pytest

from scripts.fetch_nhtsa_safety import (
    fetch_vehicle_ids,
    fetch_ratings,
    normalize_ratings,
    fetch_for_model,
)
from scripts.config import NHTSA_BASE


@responses_lib.activate
def test_fetch_vehicle_ids_returns_list(sample_nhtsa_models):
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/modelyear/2024/make/Toyota/model/Sienna",
        json=sample_nhtsa_models,
    )
    result = fetch_vehicle_ids("Toyota", "Sienna", 2024)
    assert result == [19217, 19218]


@responses_lib.activate
def test_fetch_vehicle_ids_returns_empty_on_error():
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/modelyear/2024/make/Toyota/model/Nonexistent",
        status=404,
    )
    result = fetch_vehicle_ids("Toyota", "Nonexistent", 2024)
    assert result == []


@responses_lib.activate
def test_fetch_vehicle_ids_returns_empty_when_no_results():
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/modelyear/2024/make/Toyota/model/Sienna",
        json={"Results": []},
    )
    result = fetch_vehicle_ids("Toyota", "Sienna", 2024)
    assert result == []


@responses_lib.activate
def test_fetch_ratings(sample_nhtsa_ratings):
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/VehicleId/19217",
        json=sample_nhtsa_ratings,
    )
    result = fetch_ratings(19217)
    assert result["OverallRating"] == "5"


@responses_lib.activate
def test_fetch_ratings_returns_none_on_error():
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/VehicleId/99999",
        status=500,
    )
    result = fetch_ratings(99999)
    assert result is None


def test_normalize_ratings(sample_nhtsa_ratings):
    raw = sample_nhtsa_ratings["Results"][0]
    result = normalize_ratings(raw)
    assert result["overall"] == 5
    assert result["front_crash"] == 5
    assert result["side_crash"] == 5
    assert result["rollover"] == 4
    assert result["vehicle_id"] == 19217
    assert "source_url" in result


def test_normalize_ratings_handles_not_rated():
    raw = {
        "VehicleId": 99999,
        "VehicleDescription": "2024 Test Vehicle",
        "OverallRating": "Not Rated",
        "OverallFrontCrashRating": "Not Rated",
        "OverallSideCrashRating": "Not Rated",
        "RolloverRating": "Not Rated",
    }
    result = normalize_ratings(raw)
    assert result["overall"] is None
    assert result["front_crash"] is None


def test_normalize_ratings_handles_missing_fields():
    raw = {"VehicleId": 12345}
    result = normalize_ratings(raw)
    assert result["overall"] is None
    assert result["vehicle_id"] == 12345


@responses_lib.activate
def test_fetch_for_model_full_flow(sample_nhtsa_models, sample_nhtsa_ratings):
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/modelyear/2024/make/Toyota/model/Sienna",
        json=sample_nhtsa_models,
    )
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/VehicleId/19217",
        json=sample_nhtsa_ratings,
    )
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/VehicleId/19218",
        json=sample_nhtsa_ratings,
    )
    results = fetch_for_model("Toyota", "Sienna", 2024)
    assert len(results) == 2
    assert all(r["overall"] == 5 for r in results)


@responses_lib.activate
def test_fetch_for_model_returns_empty_when_no_ids():
    responses_lib.add(
        responses_lib.GET,
        f"{NHTSA_BASE}/modelyear/2024/make/Toyota/model/Nonexistent",
        json={"Results": []},
    )
    results = fetch_for_model("Toyota", "Nonexistent", 2024)
    assert results == []
