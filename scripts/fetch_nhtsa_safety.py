"""
Fetch NHTSA 5-Star safety ratings for all target models.

Two-step process:
  1. GET /SafetyRatings/modelyear/{year}/make/{make}/model/{model}
     → returns list of VehicleId values
  2. GET /SafetyRatings/VehicleId/{vehicleId}
     → returns star ratings for that variant

Outputs raw JSON to data/raw/nhtsa_safety/{make}_{model}_{year}.json
Each file is a list of rating records (one per variant tested).
"""
import time
from typing import List, Optional

from scripts.config import (
    MODEL_YEARS,
    NHTSA_BASE,
    NHTSA_DELAY,
    RAW_DIR,
    TARGET_MODELS,
)
from scripts.utils import get_logger, get_with_retry, save_raw

logger = get_logger(__name__)

NHTSA_RAW_DIR = RAW_DIR / "nhtsa_safety"


def fetch_vehicle_ids(make: str, model: str, year: int) -> List[int]:
    """Step 1: get list of NHTSA VehicleIds for a make/model/year."""
    url = f"{NHTSA_BASE}/modelyear/{year}/make/{make}/model/{model}"
    try:
        response = get_with_retry(url)
        data = response.json()
        return [r["VehicleId"] for r in data.get("Results", [])]
    except Exception as exc:
        logger.warning("Could not fetch NHTSA vehicle IDs for %s %s %d: %s", make, model, year, exc)
        return []


def fetch_ratings(vehicle_id: int) -> Optional[dict]:
    """Step 2: get star ratings for a single NHTSA VehicleId."""
    url = f"{NHTSA_BASE}/VehicleId/{vehicle_id}"
    try:
        response = get_with_retry(url)
        data = response.json()
        results = data.get("Results", [])
        return results[0] if results else None
    except Exception as exc:
        logger.warning("Could not fetch NHTSA ratings for VehicleId %s: %s", vehicle_id, exc)
        return None


def normalize_ratings(raw: dict) -> dict:
    def star(val) -> Optional[int]:
        try:
            v = int(val)
            return v if 1 <= v <= 5 else None
        except (TypeError, ValueError):
            return None

    return {
        "vehicle_id": raw.get("VehicleId"),
        "description": raw.get("VehicleDescription"),
        "overall": star(raw.get("OverallRating")),
        "front_crash": star(raw.get("OverallFrontCrashRating")),
        "side_crash": star(raw.get("OverallSideCrashRating")),
        "rollover": star(raw.get("RolloverRating")),
        "forward_collision_warning": raw.get("NHTSAForwardCollisionWarning"),
        "lane_departure_warning": raw.get("NHTSALaneDepartureWarning"),
        "source_url": f"{NHTSA_BASE}/VehicleId/{raw.get('VehicleId')}",
    }


def fetch_for_model(make: str, model: str, year: int) -> List[dict]:
    """Fetch all NHTSA rating records for a make/model/year."""
    vehicle_ids = fetch_vehicle_ids(make, model, year)
    if not vehicle_ids:
        logger.info("No NHTSA records found: %s %s %d", make, model, year)
        return []

    records = []
    for vehicle_id in vehicle_ids:
        raw = fetch_ratings(vehicle_id)
        if raw:
            records.append(normalize_ratings(raw))
        time.sleep(NHTSA_DELAY)

    return records


def run():
    logger.info("Starting NHTSA safety fetch")
    for make, models in TARGET_MODELS.items():
        for model in models:
            for year in MODEL_YEARS:
                logger.info("Fetching NHTSA: %s %s %d", make, model, year)
                records = fetch_for_model(make, model, year)
                filename = f"{make.replace(' ', '_')}_{model.replace(' ', '_')}_{year}.json"
                save_raw(records, NHTSA_RAW_DIR, filename)
                time.sleep(NHTSA_DELAY)
    logger.info("NHTSA safety fetch complete")


if __name__ == "__main__":
    run()
