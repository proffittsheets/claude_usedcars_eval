"""
Scrape car images from manufacturer websites for all target models.

Each brand has a custom scraper strategy since sites differ.
Images are saved to data/raw/images/manufacturer/{make}/{model}/{year}/
and recorded in manifest.json.

Strategies per brand:
  - Toyota:       Media gallery og:image tags on model pages
  - Nissan:       Model page image tags with structured JSON-LD
  - Mercedes-Benz: Media images from model overview pages
  - Lincoln:      Model page gallery images

All strategies use BeautifulSoup to parse HTML.
"""
import json
import re
import time
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse

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

MAX_IMAGES_PER_MODEL = 6

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Model-to-URL-slug mappings per brand
MODEL_URL_SLUGS = {
    "Toyota": {
        "RAV4": "rav4",
        "Highlander": "highlander",
        "Sienna": "sienna",
        "Venza": "venza",
        "4Runner": "4runner",
        "Sequoia": "sequoia",
        "Camry": "camry",
    },
    "Nissan": {
        # SUVs use /vehicles/crossovers-suvs/, Altima uses /vehicles/cars/
        "Pathfinder": ("crossovers-suvs", "pathfinder"),
        "Murano": ("crossovers-suvs", "murano"),
        "Armada": ("crossovers-suvs", "armada"),
        "Rogue": ("crossovers-suvs", "rogue"),
        "Altima": ("cars", "altima"),
    },
    "Mercedes-Benz": {
        # SUVs use /en/vehicles/build/{slug}/suv, C-Class uses /sedan
        "GLC": ("glc", "suv"),
        "GLE": ("gle", "suv"),
        "GLS": ("gls", "suv"),
        "C-Class": ("c-class", "sedan"),
    },
    "Lincoln": {
        "Corsair": "corsair",
        "Nautilus": "nautilus",
        "Aviator": "aviator",
        "Navigator": "navigator",
    },
}

BRAND_BASE_URLS = {
    "Toyota": "https://www.toyota.com",
    "Nissan": "https://www.nissanusa.com",
    "Mercedes-Benz": "https://www.mbusa.com",
    "Lincoln": "https://www.lincoln.com",
}


def get_model_url(make: str, model: str) -> Optional[str]:
    """Return the manufacturer page URL for a make/model."""
    slug = MODEL_URL_SLUGS.get(make, {}).get(model)
    if not slug:
        return None
    base = BRAND_BASE_URLS.get(make, "")
    if make == "Toyota":
        return f"{base}/{slug}/"
    elif make == "Nissan":
        category, name = slug
        return f"{base}/vehicles/{category}/{name}.html"
    elif make == "Mercedes-Benz":
        model_slug, body_type = slug
        return f"{base}/en/vehicles/build/{model_slug}/{body_type}"
    elif make == "Lincoln":
        return f"{base}/vehicles/{slug}/"
    return None


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch a page and return parsed BeautifulSoup, or None on failure."""
    try:
        response = get_with_retry(url, headers=HEADERS)
        return BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def extract_og_images(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extract og:image and twitter:image meta tags."""
    urls = []
    for meta in soup.find_all("meta", property=re.compile(r"^og:image|^twitter:image")):
        content = meta.get("content", "")
        if content and content.startswith("http"):
            urls.append(content)
    return urls


def extract_json_ld_images(soup: BeautifulSoup) -> List[str]:
    """Extract image URLs from JSON-LD structured data."""
    urls = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            for item in items:
                img = item.get("image")
                if isinstance(img, str) and img.startswith("http"):
                    urls.append(img)
                elif isinstance(img, list):
                    urls.extend(i for i in img if isinstance(i, str) and i.startswith("http"))
        except (json.JSONDecodeError, AttributeError):
            continue
    return urls


def extract_gallery_images(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extract large images from img tags likely to be gallery photos."""
    urls = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src", "")
        if not src:
            continue
        # Resolve relative URLs
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            parsed = urlparse(base_url)
            src = f"{parsed.scheme}://{parsed.netloc}{src}"
        elif not src.startswith("http"):
            continue
        # Filter: skip icons, logos, small images
        skip = ["logo", "icon", "sprite", "badge", "social", "favicon", "placeholder"]
        if any(term in src.lower() for term in skip):
            continue
        # Skip data URIs and SVGs
        if src.startswith("data:") or src.endswith(".svg"):
            continue
        # Prefer large images (check width/height attrs)
        width = img.get("width", "0")
        try:
            w = int(str(width).replace("px", ""))
            if w > 0 and w < 300:
                continue
        except ValueError:
            pass
        if src not in urls:
            urls.append(src)
    return urls


def scrape_model_images(make: str, model: str) -> List[str]:
    """
    Scrape image URLs for a make/model from the manufacturer site.
    Returns deduplicated list of image URLs (not year-specific since
    manufacturer pages show current model year).
    """
    url = get_model_url(make, model)
    if not url:
        logger.warning("No URL configured for %s %s", make, model)
        return []

    logger.info("Scraping %s %s from %s", make, model, url)
    soup = fetch_page(url)
    if not soup:
        return []

    image_urls = []
    image_urls.extend(extract_og_images(soup, url))
    image_urls.extend(extract_json_ld_images(soup))
    image_urls.extend(extract_gallery_images(soup, url))

    # Deduplicate preserving order
    seen = set()
    deduped = []
    for u in image_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    return deduped[:MAX_IMAGES_PER_MODEL]


def download_image(url: str, dest_path: Path) -> bool:
    """Download image to dest_path. Returns True on success."""
    try:
        response = get_with_retry(url, headers=HEADERS, timeout=30)
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
            return json.load(f)
    return {}


def save_manifest(manifest: dict):
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def fetch_for_model(make: str, model: str, year: int) -> List[dict]:
    """
    Scrape and download manufacturer images for one make/model/year.
    Since manufacturer pages show the current model year, we only fetch
    once per make/model and tag all years. Returns manifest entries.
    """
    image_urls = scrape_model_images(make, model)
    if not image_urls:
        return []

    out_dir = (
        MANUFACTURER_OUT_DIR
        / make.replace(" ", "_")
        / model.replace(" ", "_")
        / str(year)
    )
    manifest_entries = []
    page_url = get_model_url(make, model) or BRAND_BASE_URLS.get(make, "")

    for idx, url in enumerate(image_urls):
        ext = Path(urlparse(url).path).suffix.lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"
        filename = f"{idx + 1:02d}{ext}"
        dest = out_dir / filename

        if download_image(url, dest):
            entry = {
                "local_path": str(dest.relative_to(IMAGES_DIR)),
                "source": "manufacturer",
                "source_url": page_url,
                "original_url": url,
                "license": "All rights reserved — manufacturer press image",
                "attribution": make,
                "make": make,
                "model": model,
                "year": year,
            }
            manifest_entries.append(entry)
            logger.info("Downloaded: %s", dest)
        time.sleep(MANUFACTURER_DELAY)

    return manifest_entries


def run():
    logger.info("Starting manufacturer image scrape")
    manifest = load_manifest()
    manifest.setdefault("manufacturer", [])

    for make, models in TARGET_MODELS.items():
        for model in models:
            # Only fetch the most recent year — manufacturer pages show current model
            year = max(MODEL_YEARS)
            entries = fetch_for_model(make, model, year)
            manifest["manufacturer"].extend(entries)
            save_manifest(manifest)
            time.sleep(MANUFACTURER_DELAY)

    logger.info("Manufacturer image scrape complete")


if __name__ == "__main__":
    run()
