"""
Fetch car images from Wikimedia Commons for all target models.

Strategy:
  1. Search Commons for "{year} {make} {model}" → get page titles
  2. Resolve titles to full-resolution image URLs via imageinfo API
  3. Download up to MAX_EXTERIOR images per model/year
  4. Save to data/raw/images/wikimedia/{make}/{model}/{year}/
  5. Record source URL, license, and attribution in manifest.json

Attribution is required for all Wikimedia images (Creative Commons).
"""
import json
import time
from pathlib import Path
from typing import List, Optional, Dict

import requests

from scripts.config import (
    IMAGES_DIR,
    MODEL_YEARS,
    TARGET_MODELS,
    WIKIMEDIA_API,
    WIKIMEDIA_DELAY,
)
from scripts.utils import get_logger, get_with_retry

logger = get_logger(__name__)

WIKIMEDIA_OUT_DIR = IMAGES_DIR / "wikimedia"
MANIFEST_PATH = IMAGES_DIR / "manifest.json"

MAX_IMAGES_PER_MODEL = 6  # aim for ~4 exterior, 2 interior
WIKIMEDIA_HEADERS = {
    "User-Agent": "CarVisionBoard/1.0 (research project; contact via GitHub)"
}


def search_commons(query: str, limit: int = 20) -> List[str]:
    """Search Wikimedia Commons for image titles matching query."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": 6,  # File namespace
        "srlimit": limit,
        "format": "json",
    }
    try:
        response = get_with_retry(WIKIMEDIA_API, params=params, headers=WIKIMEDIA_HEADERS)
        data = response.json()
        results = data.get("query", {}).get("search", [])
        return [r["title"] for r in results]
    except Exception as exc:
        logger.warning("Wikimedia search failed for '%s': %s", query, exc)
        return []


def get_image_info(titles: List[str]) -> List[dict]:
    """Resolve file titles to image URLs and license info."""
    if not titles:
        return []
    params = {
        "action": "query",
        "titles": "|".join(titles[:50]),  # API limit
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
        "iiurlwidth": 1200,
        "format": "json",
    }
    try:
        response = get_with_retry(WIKIMEDIA_API, params=params, headers=WIKIMEDIA_HEADERS)
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        results = []
        for page in pages.values():
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            meta = info.get("extmetadata", {})
            results.append({
                "title": page.get("title"),
                "url": info.get("url"),
                "thumb_url": info.get("thumburl"),
                "width": info.get("width"),
                "height": info.get("height"),
                "license": meta.get("LicenseShortName", {}).get("value", ""),
                "attribution": meta.get("Attribution", {}).get("value", "")
                    or meta.get("Artist", {}).get("value", ""),
                "description_url": meta.get("DescriptionUrl", {}).get("value", ""),
            })
        return results
    except Exception as exc:
        logger.warning("Wikimedia imageinfo failed: %s", exc)
        return []


def is_suitable_image(info: dict) -> bool:
    """Filter out icons, logos, diagrams — keep photos."""
    title = (info.get("title") or "").lower()
    skip_terms = ["logo", "icon", "badge", "emblem", "diagram", "map", "flag", "coat"]
    if any(term in title for term in skip_terms):
        return False
    # Prefer landscape photos (wider than tall)
    w = info.get("width") or 0
    h = info.get("height") or 0
    if h > 0 and w / h < 0.8:
        return False
    return True


def download_image(url: str, dest_path: Path) -> bool:
    """Download image to dest_path. Returns True on success."""
    try:
        response = get_with_retry(url, headers=WIKIMEDIA_HEADERS, timeout=30)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as exc:
        logger.warning("Failed to download %s: %s", url, exc)
        return False


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict):
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def fetch_for_model(make: str, model: str, year: int) -> List[dict]:
    """
    Search, download, and record images for one make/model/year.
    Returns list of manifest entries for downloaded images.
    """
    query = f"{year} {make} {model}"
    logger.info("Searching Wikimedia: %s", query)

    titles = search_commons(query)
    time.sleep(WIKIMEDIA_DELAY)

    if not titles:
        logger.info("No Wikimedia results for %s", query)
        return []

    image_infos = get_image_info(titles)
    time.sleep(WIKIMEDIA_DELAY)

    suitable = [i for i in image_infos if is_suitable_image(i)][:MAX_IMAGES_PER_MODEL]
    if not suitable:
        logger.info("No suitable images found for %s %s %d", make, model, year)
        return []

    out_dir = WIKIMEDIA_OUT_DIR / make.replace(" ", "_") / model.replace(" ", "_") / str(year)
    manifest_entries = []

    for idx, info in enumerate(suitable):
        url = info.get("url")
        if not url:
            continue
        ext = Path(url).suffix.lower() or ".jpg"
        filename = f"{idx + 1:02d}{ext}"
        dest = out_dir / filename

        if download_image(url, dest):
            entry = {
                "local_path": str(dest.relative_to(IMAGES_DIR)),
                "source": "wikimedia",
                "source_url": info.get("description_url") or url,
                "original_url": url,
                "license": info.get("license"),
                "attribution": info.get("attribution"),
                "make": make,
                "model": model,
                "year": year,
            }
            manifest_entries.append(entry)
            logger.info("Downloaded: %s", dest)
        time.sleep(WIKIMEDIA_DELAY)

    return manifest_entries


def run():
    logger.info("Starting Wikimedia image fetch")
    manifest = load_manifest()
    manifest.setdefault("wikimedia", [])

    for make, models in TARGET_MODELS.items():
        for model in models:
            for year in MODEL_YEARS:
                entries = fetch_for_model(make, model, year)
                manifest["wikimedia"].extend(entries)
                save_manifest(manifest)  # save after each model in case of interruption

    logger.info("Wikimedia image fetch complete")


if __name__ == "__main__":
    run()
