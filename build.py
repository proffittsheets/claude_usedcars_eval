"""
Site renderer: reads data/processed/catalog.json and renders all HTML pages
into the site/ directory using Jinja2 templates.

Usage:
  python build.py

Output:
  site/index.html
  site/{brand}.html  (toyota, nissan, mercedes-benz, lincoln)
  site/cars/{car-id}.html
  site/static/  (copied from static/)
"""
import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.config import PROCESSED_DIR, TARGET_MODELS
from scripts.utils import get_logger

logger = get_logger(__name__)

ROOT = Path(__file__).parent
SITE_DIR = ROOT / "site"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
CATALOG_PATH = PROCESSED_DIR / "catalog.json"


def load_catalog() -> list:
    if not CATALOG_PATH.exists():
        logger.error("catalog.json not found — run scripts/build_catalog.py first")
        return []
    with open(CATALOG_PATH) as f:
        return json.load(f)


def setup_jinja() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    return env


def copy_static():
    dest = SITE_DIR / "static"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(STATIC_DIR, dest)

    # Also copy car images from data/raw/images into site/static so paths resolve
    images_src = ROOT / "data" / "raw" / "images"
    images_dest = SITE_DIR / "data" / "raw" / "images"
    if images_src.exists():
        if images_dest.exists():
            shutil.rmtree(images_dest)
        shutil.copytree(images_src, images_dest)


def render(env: Environment, template_name: str, output_path: Path, context: dict):
    template = env.get_template(template_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template.render(**context))
    logger.info("Rendered: %s", output_path.relative_to(ROOT))


def run():
    logger.info("Building site")
    catalog = load_catalog()
    if not catalog:
        return

    env = setup_jinja()
    SITE_DIR.mkdir(exist_ok=True)
    copy_static()

    brands = list(TARGET_MODELS.keys())

    # Homepage
    render(env, "index.html", SITE_DIR / "index.html", {
        "cars": catalog,
        "brands": brands,
        "root": "",
    })

    # Per-brand pages
    for brand in brands:
        brand_cars = [c for c in catalog if c["make"] == brand]
        slug = brand.lower().replace(" ", "-")
        render(env, "brand.html", SITE_DIR / f"{slug}.html", {
            "brand": brand,
            "cars": brand_cars,
            "root": "",
        })

    # Per-car detail pages
    cars_dir = SITE_DIR / "cars"
    for car in catalog:
        render(env, "car_detail.html", cars_dir / f"{car['id']}.html", {
            "car": car,
            "root": "../",
        })

    logger.info(
        "Build complete: %d cars, %d brands → %s",
        len(catalog), len(brands), SITE_DIR,
    )


if __name__ == "__main__":
    run()
