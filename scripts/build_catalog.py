"""
ETL script: merge all raw data sources into data/processed/catalog.json

Run order:
  1. fetch_fuel_economy.py
  2. fetch_nhtsa_safety.py
  3. fetch_carquery_specs.py
  4. (image fetch scripts)
  5. python scripts/build_catalog.py

Output: data/processed/catalog.json — one entry per AWD-capable model/year variant.
"""
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from scripts.config import (
    IMAGES_DIR,
    MANUAL_DIR,
    MAX_MSRP,
    MODEL_YEARS,
    PROCESSED_DIR,
    RAW_DIR,
    TARGET_MODELS,
    get_price_tier,
)
from scripts.utils import get_logger, load_json, save_raw

logger = get_logger(__name__)

FUEL_ECONOMY_RAW = RAW_DIR / "fuel_economy"
NHTSA_RAW = RAW_DIR / "nhtsa_safety"
CARQUERY_RAW = RAW_DIR / "carquery"
MANIFEST_PATH = IMAGES_DIR / "manifest.json"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_fuel_economy(make: str, model: str, year: int) -> List[dict]:
    filename = f"{make.replace(' ', '_')}_{model.replace(' ', '_')}_{year}.json"
    data = load_json(FUEL_ECONOMY_RAW / filename)
    return data or []


def load_nhtsa(make: str, model: str, year: int) -> List[dict]:
    filename = f"{make.replace(' ', '_')}_{model.replace(' ', '_')}_{year}.json"
    data = load_json(NHTSA_RAW / filename)
    return data or []


def load_carquery(make: str, model: str, year: int) -> List[dict]:
    filename = f"{make.replace(' ', '_')}_{model.replace(' ', '_')}_{year}.json"
    data = load_json(CARQUERY_RAW / filename)
    return data or []


def load_manual(filename: str) -> dict:
    return load_json(MANUAL_DIR / filename) or {}


def best_nhtsa(records: List[dict]) -> Optional[dict]:
    """Pick the NHTSA record with the highest overall rating."""
    rated = [r for r in records if r.get("overall") is not None]
    if not rated:
        return None
    return max(rated, key=lambda r: r.get("overall") or 0)


def best_fuel_economy(records: List[dict], prefer_awd: bool = True) -> Optional[dict]:
    """Pick the fuel economy record, preferring AWD/4WD trims if available."""
    if not records:
        return None
    if prefer_awd:
        awd = [r for r in records if "awd" in (r.get("drive") or "").lower()
               or "4wd" in (r.get("drive") or "").lower()
               or "4x4" in (r.get("drive") or "").lower()
               or "all" in (r.get("drive") or "").lower()]
        if awd:
            return awd[0]
    return records[0]


def find_awd_carquery_trim(trims: List[dict]) -> Optional[dict]:
    """Return first AWD trim from CarQuery data."""
    return next((t for t in trims if t.get("has_awd")), None)


def get_images_for_model(make: str, model: str, year: int, manifest: dict) -> Dict[str, List[str]]:
    """Return exterior/interior image paths from the manifest for this model."""
    # Try chosen source preference: manufacturer first, then wikimedia
    for source in ("manufacturer", "wikimedia"):
        entries = [
            e for e in manifest.get(source, [])
            if e.get("make") == make and e.get("model") == model and e.get("year") == year
        ]
        if entries:
            return {"exterior": [e["local_path"] for e in entries], "interior": []}
    return {"exterior": [], "interior": []}


def build_entry(
    make: str,
    model: str,
    year: int,
    fe_record: dict,
    nhtsa_record: Optional[dict],
    cq_trim: Optional[dict],
    msrp_seed: dict,
    iihs: dict,
    colors: dict,
    details: dict,
    images: Dict[str, List[str]],
) -> Optional[dict]:
    """Build a single catalog entry. Returns None if entry should be excluded."""

    # Determine MSRP
    msrp = None
    if cq_trim and cq_trim.get("msrp_usd"):
        msrp = cq_trim["msrp_usd"]
    if not msrp:
        year_str = str(year)
        msrp = (msrp_seed.get(make, {}).get(model, {}).get(year_str))

    if msrp is None:
        logger.warning("No MSRP for %s %s %d — skipping", make, model, year)
        return None

    if msrp > MAX_MSRP:
        logger.info("Over budget (%s %s %d: $%d) — skipping", make, model, year, msrp)
        return None

    # Determine seat count
    seats = None
    if cq_trim:
        seats = cq_trim.get("seats")
    if not seats and fe_record:
        pass  # fueleconomy.gov doesn't provide seats

    # Body type
    body_type = cq_trim.get("body_type") if cq_trim else None

    # Safety
    safety: Dict[str, Any] = {
        "nhtsa_overall": nhtsa_record.get("overall") if nhtsa_record else None,
        "nhtsa_front_crash": nhtsa_record.get("front_crash") if nhtsa_record else None,
        "nhtsa_side_crash": nhtsa_record.get("side_crash") if nhtsa_record else None,
        "nhtsa_rollover": nhtsa_record.get("rollover") if nhtsa_record else None,
        "nhtsa_source_url": nhtsa_record.get("source_url") if nhtsa_record else None,
    }
    iihs_rating = iihs.get(make, {}).get(model, {}).get(str(year))
    safety["iihs_overall"] = iihs_rating
    safety["iihs_source_url"] = "https://www.iihs.org/ratings/top-safety-picks"

    # Minor details
    model_details = details.get(make, {}).get(model, {})

    # Color options
    color_options = colors.get(make, {}).get(model, [])

    # Build ID
    entry_id = slugify(f"{make}-{model}-{year}")

    return {
        "id": entry_id,
        "make": make,
        "model": model,
        "year": year,
        "body_type": body_type,
        "has_awd": True,  # invariant: all entries must have AWD
        "is_hybrid": fe_record.get("is_hybrid", False) if fe_record else False,
        "price_tier": get_price_tier(msrp),
        "msrp_usd": msrp,
        "seats": seats,
        "mpg_city": fe_record.get("mpg_city") if fe_record else None,
        "mpg_highway": fe_record.get("mpg_highway") if fe_record else None,
        "mpg_combined": fe_record.get("mpg_combined") if fe_record else None,
        "fuel_type": fe_record.get("fuel_type") if fe_record else None,
        "color_options": color_options,
        "safety": safety,
        "details": model_details,
        "images": images,
        "source_urls": {
            "manufacturer": _manufacturer_url(make, model),
            "fuel_economy": fe_record.get("source_url") if fe_record else None,
            "nhtsa_safety": nhtsa_record.get("source_url") if nhtsa_record else None,
        },
    }


def _manufacturer_url(make: str, model: str) -> str:
    slug = model.lower().replace(" ", "-").replace("/", "-")
    urls = {
        "Toyota": f"https://www.toyota.com/{slug.replace('-', '')}/",
        "Nissan": f"https://www.nissanusa.com/vehicles/{slug}/",
        "Mercedes-Benz": f"https://www.mbusa.com/en/vehicles/class/{slug}/overview.html",
        "Lincoln": f"https://www.lincoln.com/vehicles/{slug}/",
    }
    return urls.get(make, "")


def run() -> List[dict]:
    logger.info("Building catalog")

    msrp_seed = load_manual("msrp_seed.json")
    iihs = load_manual("iihs_overrides.json")
    colors = load_manual("color_options.json")
    details = load_manual("details_overrides.json")
    manifest = load_json(MANIFEST_PATH) or {}

    catalog = []

    for make, models in TARGET_MODELS.items():
        for model in models:
            for year in MODEL_YEARS:
                fe_records = load_fuel_economy(make, model, year)
                nhtsa_records = load_nhtsa(make, model, year)
                cq_trims = load_carquery(make, model, year)

                # Pick best records
                fe_record = best_fuel_economy(fe_records, prefer_awd=True)
                nhtsa_record = best_nhtsa(nhtsa_records)
                cq_trim = find_awd_carquery_trim(cq_trims)

                # Skip if no AWD trim found in CarQuery AND no fuel economy AWD record
                fe_has_awd = fe_record and (
                    "awd" in (fe_record.get("drive") or "").lower()
                    or "4wd" in (fe_record.get("drive") or "").lower()
                    or "all" in (fe_record.get("drive") or "").lower()
                )
                if not cq_trim and not fe_has_awd:
                    # Still include if MSRP seed exists — some models have AWD we know about
                    year_msrp = msrp_seed.get(make, {}).get(model, {}).get(str(year))
                    if not year_msrp:
                        logger.info("No AWD data and no MSRP: skipping %s %s %d", make, model, year)
                        continue

                images = get_images_for_model(make, model, year, manifest)

                entry = build_entry(
                    make, model, year,
                    fe_record, nhtsa_record, cq_trim,
                    msrp_seed, iihs, colors, details, images,
                )
                if entry:
                    catalog.append(entry)
                    logger.info("Added: %s %s %d ($%d, %s)", make, model, year, entry["msrp_usd"], entry["price_tier"])

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    save_raw(catalog, PROCESSED_DIR, "catalog.json")
    logger.info("Catalog complete: %d entries → data/processed/catalog.json", len(catalog))
    return catalog


if __name__ == "__main__":
    run()
