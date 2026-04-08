"""
Scrape car images from manufacturer and editorial sources.

Strategies per brand:
  - Toyota:       Toyota Pressroom (pressroom.toyota.com) — year-specific S3 press images
  - Nissan:       Motor Trend editorial pages — year-specific Hearst CDN images
  - Mercedes-Benz: Motor Trend editorial pages — year-specific Hearst CDN images
  - Lincoln:      Motor Trend editorial pages — year-specific Hearst CDN images

Images are saved to data/raw/images/manufacturer/{make}/{model}/{year}/
and recorded in manifest.json.
"""
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scripts.config import (
    IMAGES_DIR,
    MANUFACTURER_DELAY,
    MODEL_YEARS,
    TARGET_MODELS,
)
from scripts.utils import get_logger, get_with_retry

logger = get_logger(__name__)

MANUFACTURER_OUT_DIR = IMAGES_DIR / "manufacturer"
MANIFEST_PATH = IMAGES_DIR / "manifest.json"

MAX_IMAGES_PER_MODEL = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Toyota Pressroom URL slugs — year-specific pages exist for all except Venza 2025/2026
TOYOTA_PRESSROOM_SLUGS = {
    "RAV4": "rav4",
    "Highlander": "highlander",
    "Sienna": "sienna",
    "Venza": "venza",
    "4Runner": "4runner",
    "Sequoia": "sequoia",
    "Camry": "camry",
}

# Toyota Pressroom 404s for these model/year combos — leave to Wikimedia fallback
TOYOTA_PRESSROOM_SKIP = {
    ("Venza", 2025),
    ("Venza", 2026),
}

# Motor Trend brand/model slugs for motortrend.com/cars/{brand}/{model}/{year}
MOTOR_TREND_SLUGS = {
    "Nissan": {
        "brand": "nissan",
        "models": {
            "Pathfinder": "pathfinder",
            "Murano": "murano",
            "Armada": "armada",
            "Rogue": "rogue",
            "Altima": "altima",
        },
    },
    "Mercedes-Benz": {
        "brand": "mercedes-benz",
        "models": {
            "GLC": "glc-class",
            "GLE": "gle-class",
            "GLS": "gls",
            "C-Class": "c-class",
        },
    },
    "Lincoln": {
        "brand": "lincoln",
        "models": {
            "Corsair": "corsair",
            "Nautilus": "nautilus",
            "Aviator": "aviator",
            "Navigator": "navigator",
        },
    },
    "Honda": {
        "brand": "honda",
        "models": {
            "Pilot": "pilot",
            "CR-V": "cr-v",
            "Passport": "passport",
            "Odyssey": "odyssey",
        },
    },
    "Volkswagen": {
        "brand": "volkswagen",
        "models": {
            "Atlas": "atlas",
            "Tiguan": "tiguan",
            "ID.4": "id-4",
        },
    },
}

# Regex to detect and measure size suffixes like -1500x900 in image filenames
_SIZE_RE = re.compile(r"-(\d+)x(\d+)(?=\.\w{2,5}$)", re.IGNORECASE)


def _image_base_key(url: str) -> str:
    """Return a dedup key by stripping size suffix from the URL stem."""
    path = urlparse(url).path
    cleaned = _SIZE_RE.sub("", path)
    return Path(cleaned).stem


def _image_area(url: str) -> int:
    """Return pixel area from a size suffix, or 0 if none."""
    m = _SIZE_RE.search(url)
    return int(m.group(1)) * int(m.group(2)) if m else 0


def scrape_toyota_pressroom(model_slug: str, year: int) -> List[str]:
    """
    Scrape year-specific press images from Toyota Pressroom.
    Returns deduplicated S3 image URLs, largest size per unique image.
    """
    url = f"https://pressroom.toyota.com/vehicle/{year}-toyota-{model_slug}/"
    logger.info("Scraping Toyota Pressroom: %s", url)

    try:
        response = get_with_retry(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        logger.warning("Failed to fetch Toyota Pressroom %s: %s", url, exc)
        return []

    s3_prefix = "toyota-cms-media.s3.amazonaws.com"
    # best[base_key] = (area, url)
    best: dict = {}

    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            src = img.get(attr, "")
            if s3_prefix in src:
                key = _image_base_key(src)
                area = _image_area(src)
                if key not in best or area > best[key][0]:
                    best[key] = (area, src)

        srcset = img.get("srcset", "")
        for part in srcset.split(","):
            src = part.strip().split()[0] if part.strip() else ""
            if s3_prefix in src:
                key = _image_base_key(src)
                area = _image_area(src)
                if key not in best or area > best[key][0]:
                    best[key] = (area, src)

    results = [url for _, url in best.values()]
    logger.info("Found %d unique Toyota Pressroom images for %s %d", len(results), model_slug, year)
    return results[:MAX_IMAGES_PER_MODEL]


def _mt_model_keywords(model_slug: str) -> List[str]:
    """Extract meaningful model-identifying keywords from a Motor Trend model slug."""
    # Strip generic words that appear in many filenames
    stopwords = {"class", "the", "and", "for"}
    return [w for w in re.split(r"[-_]", model_slug) if len(w) >= 3 and w not in stopwords]


def _mt_filename_matches_model(url: str, model_slug: str) -> bool:
    """Return True if the URL filename contains a model-identifying keyword."""
    from urllib.parse import urlparse as _up
    filename = Path(_up(url).path).stem.lower()
    for kw in _mt_model_keywords(model_slug):
        if kw in filename:
            return True
    return False


def _mt_filename_matches_year(url: str, year: int) -> bool:
    from urllib.parse import urlparse as _up
    return str(year) in Path(_up(url).path).stem.lower()


def scrape_motor_trend(brand_slug: str, model_slug: str, year: int) -> List[str]:
    """
    Scrape year-specific images from Motor Trend editorial pages.
    Returns Hearst CDN (mtg-prod) image URLs for the target vehicle only.
    """
    url = f"https://www.motortrend.com/cars/{brand_slug}/{model_slug}/{year}"
    logger.info("Scraping Motor Trend: %s", url)

    try:
        response = get_with_retry(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        logger.warning("Failed to fetch Motor Trend page %s: %s", url, exc)
        return []

    cdn_prefix = "hips.hearstapps.com/mtg-prod/"
    # best[path] = (width, full_url) — dedup by base path, keep largest width
    best: dict = {}

    def _width(url: str) -> int:
        from urllib.parse import parse_qs, urlparse as _up
        qs = parse_qs(_up(url).query)
        for key in ("w", "width"):
            if key in qs:
                try:
                    return int(qs[key][0])
                except (ValueError, IndexError):
                    pass
        return 0

    # Collect all candidate URLs, deduped by base path keeping largest width
    all_best: dict = {}

    def _collect(src: str):
        src = src.strip()
        if cdn_prefix not in src:
            return
        base = src.split("?")[0]
        w = _width(src)
        if base not in all_best or w > all_best[base][0]:
            all_best[base] = (w, src)

    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            _collect(img.get(attr, ""))
        for part in img.get("srcset", "").split(","):
            _collect(part.strip().split()[0] if part.strip() else "")

    for source in soup.find_all("source"):
        for part in source.get("srcset", "").split(","):
            _collect(part.strip().split()[0] if part.strip() else "")

    all_urls = [u for _, u in all_best.values()]

    # Pass 1: model-name match (most precise — filters out sidebar/related images)
    model_matched = [u for u in all_urls if _mt_filename_matches_model(u, model_slug)]

    # Pass 2: fall back to year match only if too few model matches
    if len(model_matched) >= 3:
        image_urls = model_matched
    else:
        year_matched = [u for u in all_urls if _mt_filename_matches_year(u, year)]
        image_urls = model_matched + [u for u in year_matched if u not in model_matched]
        if not image_urls:
            image_urls = all_urls  # last resort: take everything

    logger.info("Found %d Motor Trend images for %s/%s %d", len(image_urls), brand_slug, model_slug, year)
    return image_urls[:MAX_IMAGES_PER_MODEL]


def scrape_model_images(make: str, model: str, year: int) -> Tuple[List[str], str]:
    """
    Dispatch to the correct scraper for a make/model/year.
    Returns (image_urls, source_page_url).
    An empty list means no images were found — Wikimedia fallback applies.
    """
    if make == "Toyota":
        slug = TOYOTA_PRESSROOM_SLUGS.get(model)
        if not slug:
            logger.warning("No Toyota Pressroom slug for %s", model)
            return [], ""
        if (model, year) in TOYOTA_PRESSROOM_SKIP:
            logger.info("Toyota %s %d: no Pressroom page — leaving to Wikimedia", model, year)
            return [], ""
        page_url = f"https://pressroom.toyota.com/vehicle/{year}-toyota-{slug}/"
        return scrape_toyota_pressroom(slug, year), page_url

    brand_config = MOTOR_TREND_SLUGS.get(make, {})
    brand_slug = brand_config.get("brand", "")
    model_slug = brand_config.get("models", {}).get(model, "")
    if not brand_slug or not model_slug:
        logger.warning("No Motor Trend slug configured for %s %s", make, model)
        return [], ""
    page_url = f"https://www.motortrend.com/cars/{brand_slug}/{model_slug}/{year}"
    return scrape_motor_trend(brand_slug, model_slug, year), page_url


def download_image(url: str, dest_path: Path, extra_headers: Optional[dict] = None) -> bool:
    """Download image to dest_path. Returns True on success."""
    try:
        headers = {**HEADERS, **(extra_headers or {})}
        response = get_with_retry(url, headers=headers, timeout=30)
        content_type = response.headers.get("content-type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            logger.warning("Skipping non-image content-type '%s' for %s", content_type, url)
            return False
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
            import json
            return json.load(f)
    return {}


def save_manifest(manifest: dict):
    import json
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def _attribution_for(make: str) -> Tuple[str, str]:
    """Return (attribution, license) strings for a make."""
    if make == "Toyota":
        return (
            "Toyota Motor North America Pressroom",
            "All rights reserved — Toyota Motor North America (personal research use)",
        )
    return (
        "Motor Trend / Hearst Autos",
        "All rights reserved — Hearst Autos (personal research use)",
    )


def fetch_for_model(make: str, model: str, year: int) -> List[dict]:
    """
    Scrape and download manufacturer/editorial images for one make/model/year.
    Returns manifest entries for successfully downloaded images.
    """
    image_urls, page_url = scrape_model_images(make, model, year)
    if not image_urls:
        return []

    out_dir = (
        MANUFACTURER_OUT_DIR
        / make.replace(" ", "_")
        / model.replace(" ", "_")
        / str(year)
    )
    attribution, license_text = _attribution_for(make)
    # Toyota S3 images require a Referer header matching the pressroom domain
    download_extra_headers = (
        {"Referer": "https://pressroom.toyota.com/"} if make == "Toyota" else None
    )
    manifest_entries = []

    for idx, url in enumerate(image_urls):
        ext = Path(urlparse(url).path).suffix.lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"
        filename = f"{idx + 1:02d}{ext}"
        dest = out_dir / filename

        if download_image(url, dest, extra_headers=download_extra_headers):
            entry = {
                "local_path": str(dest.relative_to(IMAGES_DIR)),
                "source": "manufacturer",
                "source_url": page_url,
                "original_url": url,
                "license": license_text,
                "attribution": attribution,
                "make": make,
                "model": model,
                "year": year,
            }
            manifest_entries.append(entry)
            logger.info("Downloaded: %s", dest)
        time.sleep(0.5)  # Short delay between image downloads (CDN, not rate-limited)

    return manifest_entries


def run():
    logger.info("Starting manufacturer image scrape")
    manifest = load_manifest()
    manifest.setdefault("manufacturer", [])

    for make, models in TARGET_MODELS.items():
        for model in models:
            for year in MODEL_YEARS:
                out_dir = (
                    MANUFACTURER_OUT_DIR
                    / make.replace(" ", "_")
                    / model.replace(" ", "_")
                    / str(year)
                )
                img_exts = {".jpg", ".jpeg", ".png", ".webp"}
                if out_dir.exists() and any(f.suffix.lower() in img_exts for f in out_dir.iterdir()):
                    logger.info("Skipping %s %s %d (images already on disk)", make, model, year)
                    continue
                entries = fetch_for_model(make, model, year)
                manifest["manufacturer"].extend(entries)
                save_manifest(manifest)
                time.sleep(MANUFACTURER_DELAY)

    logger.info("Manufacturer image scrape complete")


if __name__ == "__main__":
    run()
