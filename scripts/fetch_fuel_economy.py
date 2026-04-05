"""
Fetch MPG and hybrid data from fueleconomy.gov for all target models.

The API returns XML only. Model names in the API include drivetrain suffixes
(e.g. "Sienna AWD", "4Runner 4WD") so we do a prefix match against our
target model name.

Outputs raw JSON files to data/raw/fuel_economy/{make}_{model}_{year}.json
Each file is a list of vehicle records (one per trim/option set).
"""
import time
import xml.etree.ElementTree as ET
from typing import List, Optional

from scripts.config import (
    FUEL_ECONOMY_BASE,
    FUEL_ECONOMY_DELAY,
    FUEL_ECONOMY_MODEL_PREFIXES,
    MODEL_YEARS,
    RAW_DIR,
    TARGET_MODELS,
)
from scripts.utils import get_logger, get_with_retry, save_raw

logger = get_logger(__name__)

FUEL_ECONOMY_RAW_DIR = RAW_DIR / "fuel_economy"


def _parse_menu_items(xml_text: str) -> List[dict]:
    """Parse <menuItems><menuItem><text>...</text><value>...</value></menuItem>...</menuItems>"""
    try:
        root = ET.fromstring(xml_text)
        items = []
        for item in root.findall("menuItem"):
            text  = item.findtext("text", "")
            value = item.findtext("value", "")
            if value:
                items.append({"text": text, "value": value})
        return items
    except ET.ParseError as exc:
        logger.warning("XML parse error in menu items: %s", exc)
        return []


def _parse_vehicle_record(xml_text: str) -> Optional[dict]:
    """Parse a fueleconomy.gov vehicle XML record into a flat dict."""
    try:
        root = ET.fromstring(xml_text)
        return {child.tag: child.text for child in root}
    except ET.ParseError as exc:
        logger.warning("XML parse error in vehicle record: %s", exc)
        return None


def get_api_model_names(make: str, model: str, year: int) -> List[str]:
    """
    Return all API model-name values for a make/year that match our target model.
    The API uses names like 'Sienna AWD', 'Sienna FWD', '4Runner 4WD' so we
    match any name that starts with our model name (case-insensitive).
    """
    url = f"{FUEL_ECONOMY_BASE}/vehicle/menu/model"
    params = {"year": year, "make": make}
    try:
        response = get_with_retry(url, params=params)
        all_models = _parse_menu_items(response.text)
        prefix = FUEL_ECONOMY_MODEL_PREFIXES.get((make, model), model).lower()
        return [
            m["value"] for m in all_models
            if m["value"].lower().startswith(prefix)
        ]
    except Exception as exc:
        logger.warning("Could not list models for %s %d: %s", make, year, exc)
        return []


def fetch_vehicle_ids(make: str, api_model_name: str, year: int) -> List[dict]:
    """Return list of {value, text} option dicts for a make/api_model_name/year."""
    url = f"{FUEL_ECONOMY_BASE}/vehicle/menu/options"
    params = {"year": year, "make": make, "model": api_model_name}
    try:
        response = get_with_retry(url, params=params)
        return _parse_menu_items(response.text)
    except Exception as exc:
        logger.warning("Could not fetch vehicle IDs for %s %s %d: %s", make, api_model_name, year, exc)
        return []


def fetch_vehicle_record(vehicle_id: str) -> Optional[dict]:
    """Return full vehicle record dict for a fueleconomy.gov vehicle ID."""
    url = f"{FUEL_ECONOMY_BASE}/vehicle/{vehicle_id}"
    try:
        response = get_with_retry(url)
        return _parse_vehicle_record(response.text)
    except Exception as exc:
        logger.warning("Could not fetch vehicle record %s: %s", vehicle_id, exc)
        return None


def is_hybrid(record: dict) -> bool:
    atv_type = record.get("atvType", "") or ""
    fuel_type = record.get("fuelType1", "") or ""
    return (
        atv_type.lower() in ("hybrid", "plug-in hybrid/electric")
        or "electric" in fuel_type.lower()
    )


def normalize_record(record: dict) -> dict:
    def _int(val):
        try:
            return int(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    return {
        "vehicle_id": str(record.get("id", "")),
        "year": _int(record.get("year")),
        "make": record.get("make"),
        "model": record.get("model"),
        "trany": record.get("trany"),
        "drive": record.get("drive"),
        "fuel_type": record.get("fuelType1"),
        "atv_type": record.get("atvType"),
        "is_hybrid": is_hybrid(record),
        "mpg_city": _int(record.get("city08")),
        "mpg_highway": _int(record.get("highway08")),
        "mpg_combined": _int(record.get("comb08")),
        "mpg_city_alt": _int(record.get("cityA08")),
        "mpg_highway_alt": _int(record.get("highwayA08")),
        "mpg_combined_alt": _int(record.get("combA08")),
        "annual_fuel_cost": _int(record.get("fuelCost08")),
        "source_url": f"https://www.fueleconomy.gov/feg/Find.do?action=sbs&id={record.get('id', '')}",
    }


def fetch_for_model(make: str, model: str, year: int) -> List[dict]:
    """Fetch all trim records for a make/model/year. Returns list of normalized records."""
    api_model_names = get_api_model_names(make, model, year)
    if not api_model_names:
        logger.info("No API model names found: %s %s %d", make, model, year)
        return []

    logger.info("API model names for %s %s %d: %s", make, model, year, api_model_names)

    all_records = []
    for api_model_name in api_model_names:
        options = fetch_vehicle_ids(make, api_model_name, year)
        time.sleep(FUEL_ECONOMY_DELAY)
        for option in options:
            vehicle_id = option.get("value")
            if not vehicle_id:
                continue
            record = fetch_vehicle_record(vehicle_id)
            if record:
                all_records.append(normalize_record(record))
            time.sleep(FUEL_ECONOMY_DELAY)

    return all_records


def run():
    logger.info("Starting fuel economy fetch")
    for make, models in TARGET_MODELS.items():
        for model in models:
            for year in MODEL_YEARS:
                logger.info("Fetching: %s %s %d", make, model, year)
                records = fetch_for_model(make, model, year)
                filename = f"{make.replace(' ', '_')}_{model.replace(' ', '_')}_{year}.json"
                save_raw(records, FUEL_ECONOMY_RAW_DIR, filename)
                time.sleep(FUEL_ECONOMY_DELAY)
    logger.info("Fuel economy fetch complete")


if __name__ == "__main__":
    run()
