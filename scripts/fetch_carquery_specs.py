"""
Fetch vehicle specs from CarQuery API for all target models.

CarQuery returns JSONP. We strip the wrapper and parse JSON.
Outputs raw JSON to data/raw/carquery/{make}_{model}_{year}.json

Extracts: body type, drivetrain, seat count, doors, transmission, MSRP.
"""
import time
from typing import List, Optional

from scripts.config import (
    CARQUERY_BASE,
    CARQUERY_DELAY,
    MODEL_YEARS,
    RAW_DIR,
    TARGET_MODELS,
)
from scripts.utils import get_logger, get_with_retry, save_raw, strip_jsonp

logger = get_logger(__name__)

CARQUERY_RAW_DIR = RAW_DIR / "carquery"

AWD_TERMS = {"awd", "4wd", "4x4", "all wheel drive", "all-wheel drive", "four wheel drive"}


def fetch_trims(make: str, model: str, year: int) -> List[dict]:
    """Fetch trim data from CarQuery. Returns list of raw trim dicts."""
    params = {
        "cmd": "getTrims",
        "make": make.lower().replace("-", "").replace(" ", ""),
        "model": model.lower().replace("-", " "),
        "year": year,
        "sold_in_us": 1,
        "callback": "?",
    }
    try:
        response = get_with_retry(CARQUERY_BASE, params=params)
        data = strip_jsonp(response.text)
        return data.get("Trims", [])
    except Exception as exc:
        logger.warning("Could not fetch CarQuery trims for %s %s %d: %s", make, model, year, exc)
        return []


def has_awd(drive: str) -> bool:
    return drive.lower().strip() in AWD_TERMS if drive else False


def normalize_body_type(body: str) -> Optional[str]:
    if not body:
        return None
    body_lower = body.lower()
    if "minivan" in body_lower or "van" in body_lower:
        return "Minivan"
    if "sport utility" in body_lower or "suv" in body_lower or "crossover" in body_lower:
        return "SUV"
    if "sedan" in body_lower or "saloon" in body_lower:
        return "Sedan"
    return body.strip()


def normalize_trim(raw: dict) -> dict:
    msrp = raw.get("model_msrp")
    try:
        msrp_usd = int(float(msrp)) if msrp else None
    except (ValueError, TypeError):
        msrp_usd = None

    seats = raw.get("model_seats")
    try:
        seats = int(seats) if seats else None
    except (ValueError, TypeError):
        seats = None

    drive = raw.get("model_drive", "")

    return {
        "trim_id": raw.get("model_id"),
        "make": raw.get("model_make_id", "").title(),
        "model": raw.get("model_name"),
        "year": raw.get("model_year"),
        "trim": raw.get("model_trim"),
        "body_type": normalize_body_type(raw.get("model_body", "")),
        "doors": raw.get("model_doors"),
        "seats": seats,
        "drive": drive,
        "has_awd": has_awd(drive),
        "transmission": raw.get("model_transmission_type"),
        "msrp_usd": msrp_usd,
        "sold_in_us": raw.get("model_sold_in_us") == "1",
    }


def fetch_for_model(make: str, model: str, year: int) -> List[dict]:
    trims = fetch_trims(make, model, year)
    if not trims:
        logger.info("No CarQuery trims found: %s %s %d", make, model, year)
        return []
    return [normalize_trim(t) for t in trims]


def run():
    logger.info("Starting CarQuery specs fetch")
    for make, models in TARGET_MODELS.items():
        for model in models:
            for year in MODEL_YEARS:
                logger.info("Fetching CarQuery: %s %s %d", make, model, year)
                records = fetch_for_model(make, model, year)
                filename = f"{make.replace(' ', '_')}_{model.replace(' ', '_')}_{year}.json"
                save_raw(records, CARQUERY_RAW_DIR, filename)
                time.sleep(CARQUERY_DELAY)
    logger.info("CarQuery fetch complete")


if __name__ == "__main__":
    run()
