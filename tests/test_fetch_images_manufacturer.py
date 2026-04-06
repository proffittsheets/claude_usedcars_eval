import json
from pathlib import Path
from unittest.mock import patch

import pytest
import responses as responses_lib

from scripts.fetch_images_manufacturer import (
    _image_base_key,
    _image_area,
    scrape_toyota_pressroom,
    scrape_motor_trend,
    scrape_model_images,
    download_image,
    fetch_for_model,
)

# ---------------------------------------------------------------------------
# Helpers: _image_base_key / _image_area
# ---------------------------------------------------------------------------

def test_image_base_key_strips_size_suffix():
    url = "https://toyota-cms-media.s3.amazonaws.com/wp-content/2025-rav4-exterior-01-1500x900.jpg"
    assert _image_base_key(url) == "2025-rav4-exterior-01"


def test_image_base_key_no_suffix():
    url = "https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue-front.jpg"
    assert _image_base_key(url) == "2025-nissan-rogue-front"


def test_image_area_detects_dimensions():
    url = "https://example.com/car-1500x900.jpg"
    assert _image_area(url) == 1500 * 900


def test_image_area_returns_zero_when_no_suffix():
    url = "https://example.com/car.jpg"
    assert _image_area(url) == 0


# ---------------------------------------------------------------------------
# scrape_toyota_pressroom
# ---------------------------------------------------------------------------

_PRESSROOM_HTML = """
<html><body>
  <img src="https://toyota-cms-media.s3.amazonaws.com/wp-content/uploads/2025-rav4-exterior-01-1500x900.jpg"/>
  <img src="https://toyota-cms-media.s3.amazonaws.com/wp-content/uploads/2025-rav4-exterior-01-800x480.jpg"/>
  <img src="https://toyota-cms-media.s3.amazonaws.com/wp-content/uploads/2025-rav4-interior-01-1500x900.jpg"/>
  <img src="https://example.com/not-toyota.jpg"/>
</body></html>
"""


@responses_lib.activate
def test_scrape_toyota_pressroom_returns_s3_urls():
    responses_lib.add(
        responses_lib.GET,
        "https://pressroom.toyota.com/vehicle/2025-toyota-rav4/",
        body=_PRESSROOM_HTML,
    )
    urls = scrape_toyota_pressroom("rav4", 2025)
    assert all("toyota-cms-media.s3.amazonaws.com" in u for u in urls)
    assert "https://example.com/not-toyota.jpg" not in urls


@responses_lib.activate
def test_scrape_toyota_pressroom_deduplicates_by_size():
    # exterior-01 appears at two sizes — should only keep the 1500x900 version
    responses_lib.add(
        responses_lib.GET,
        "https://pressroom.toyota.com/vehicle/2025-toyota-rav4/",
        body=_PRESSROOM_HTML,
    )
    urls = scrape_toyota_pressroom("rav4", 2025)
    exterior_urls = [u for u in urls if "exterior-01" in u]
    assert len(exterior_urls) == 1
    assert "1500x900" in exterior_urls[0]


@responses_lib.activate
def test_scrape_toyota_pressroom_404_returns_empty():
    responses_lib.add(
        responses_lib.GET,
        "https://pressroom.toyota.com/vehicle/2025-toyota-venza/",
        status=404,
    )
    urls = scrape_toyota_pressroom("venza", 2025)
    assert urls == []


@responses_lib.activate
def test_scrape_toyota_pressroom_parses_srcset():
    html = """
    <html><body>
      <img srcset="https://toyota-cms-media.s3.amazonaws.com/2025-sienna-exterior-01-800x480.jpg 800w,
                   https://toyota-cms-media.s3.amazonaws.com/2025-sienna-exterior-01-1500x900.jpg 1500w"/>
    </body></html>
    """
    responses_lib.add(
        responses_lib.GET,
        "https://pressroom.toyota.com/vehicle/2025-toyota-sienna/",
        body=html,
    )
    urls = scrape_toyota_pressroom("sienna", 2025)
    assert len(urls) == 1
    assert "1500x900" in urls[0]


# ---------------------------------------------------------------------------
# scrape_motor_trend
# ---------------------------------------------------------------------------

_MT_HTML = """
<html><body>
  <img src="https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue-front-view.jpg"/>
  <img src="https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue-side-view.jpg"/>
  <img src="https://example.com/other-image.jpg"/>
  <img src="https://hips.hearstapps.com/hmg-prod/not-mtg-prod.jpg"/>
</body></html>
"""


@responses_lib.activate
def test_scrape_motor_trend_returns_mtg_urls():
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/cars/nissan/rogue/2025",
        body=_MT_HTML,
    )
    urls = scrape_motor_trend("nissan", "rogue", 2025)
    assert "https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue-front-view.jpg" in urls
    assert "https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue-side-view.jpg" in urls


@responses_lib.activate
def test_scrape_motor_trend_filters_non_mtg_cdn():
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/cars/nissan/rogue/2025",
        body=_MT_HTML,
    )
    urls = scrape_motor_trend("nissan", "rogue", 2025)
    assert "https://example.com/other-image.jpg" not in urls
    assert all("mtg-prod" in u for u in urls)


@responses_lib.activate
def test_scrape_motor_trend_404_returns_empty():
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/cars/lincoln/navigator/2026",
        status=404,
    )
    urls = scrape_motor_trend("lincoln", "navigator", 2026)
    assert urls == []


@responses_lib.activate
def test_scrape_motor_trend_parses_picture_srcset():
    html = """
    <html><body>
      <picture>
        <source srcset="https://hips.hearstapps.com/mtg-prod/2025-lincoln-corsair-exterior.jpg 1200w"/>
        <img src="https://hips.hearstapps.com/mtg-prod/2025-lincoln-corsair-exterior-small.jpg"/>
      </picture>
    </body></html>
    """
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/cars/lincoln/corsair/2025",
        body=html,
    )
    urls = scrape_motor_trend("lincoln", "corsair", 2025)
    assert len(urls) == 2
    assert all("mtg-prod" in u for u in urls)


@responses_lib.activate
def test_scrape_motor_trend_deduplicates():
    html = """
    <html><body>
      <img src="https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue-front.jpg"/>
      <img src="https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue-front.jpg"/>
    </body></html>
    """
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/cars/nissan/rogue/2025",
        body=html,
    )
    urls = scrape_motor_trend("nissan", "rogue", 2025)
    assert len(urls) == 1


# ---------------------------------------------------------------------------
# scrape_model_images dispatch
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_scrape_model_images_dispatches_toyota_to_pressroom():
    responses_lib.add(
        responses_lib.GET,
        "https://pressroom.toyota.com/vehicle/2025-toyota-rav4/",
        body='<html><body><img src="https://toyota-cms-media.s3.amazonaws.com/rav4-2025.jpg"/></body></html>',
    )
    urls, page_url = scrape_model_images("Toyota", "RAV4", 2025)
    assert "pressroom.toyota.com" in page_url
    assert any("toyota-cms-media" in u for u in urls)


@responses_lib.activate
def test_scrape_model_images_dispatches_nissan_to_motor_trend():
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/cars/nissan/rogue/2025",
        body='<html><body><img src="https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue.jpg"/></body></html>',
    )
    urls, page_url = scrape_model_images("Nissan", "Rogue", 2025)
    assert "motortrend.com" in page_url
    assert any("mtg-prod" in u for u in urls)


@responses_lib.activate
def test_scrape_model_images_dispatches_mercedes_to_motor_trend():
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/cars/mercedes-benz/glc-class/2024",
        body='<html><body><img src="https://hips.hearstapps.com/mtg-prod/2024-mercedes-glc.jpg"/></body></html>',
    )
    urls, page_url = scrape_model_images("Mercedes-Benz", "GLC", 2024)
    assert "motortrend.com" in page_url
    assert any("mtg-prod" in u for u in urls)


def test_scrape_model_images_venza_2025_skips_pressroom():
    urls, page_url = scrape_model_images("Toyota", "Venza", 2025)
    assert urls == []
    assert page_url == ""


def test_scrape_model_images_venza_2026_skips_pressroom():
    urls, page_url = scrape_model_images("Toyota", "Venza", 2026)
    assert urls == []
    assert page_url == ""


def test_scrape_model_images_unknown_model_returns_empty():
    urls, page_url = scrape_model_images("Toyota", "UnknownModel", 2025)
    assert urls == []
    assert page_url == ""


# ---------------------------------------------------------------------------
# download_image
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_download_image_success(tmp_path):
    responses_lib.add(
        responses_lib.GET,
        "https://toyota-cms-media.s3.amazonaws.com/rav4.jpg",
        body=b"fake image bytes",
        headers={"content-type": "image/jpeg"},
    )
    dest = tmp_path / "rav4.jpg"
    assert download_image("https://toyota-cms-media.s3.amazonaws.com/rav4.jpg", dest) is True
    assert dest.read_bytes() == b"fake image bytes"


@responses_lib.activate
def test_download_image_skips_non_image(tmp_path):
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/page.html",
        body=b"<html></html>",
        headers={"content-type": "text/html"},
    )
    dest = tmp_path / "page.html"
    assert download_image("https://www.motortrend.com/page.html", dest) is False
    assert not dest.exists()


# ---------------------------------------------------------------------------
# fetch_for_model
# ---------------------------------------------------------------------------

@responses_lib.activate
def test_fetch_for_model_toyota_downloads_and_records(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.fetch_images_manufacturer.MANUFACTURER_OUT_DIR", tmp_path / "manufacturer")
    monkeypatch.setattr("scripts.fetch_images_manufacturer.IMAGES_DIR", tmp_path)

    pressroom_html = '<html><body><img src="https://toyota-cms-media.s3.amazonaws.com/2025-sienna-01-1500x900.jpg"/></body></html>'
    responses_lib.add(
        responses_lib.GET,
        "https://pressroom.toyota.com/vehicle/2025-toyota-sienna/",
        body=pressroom_html,
    )
    responses_lib.add(
        responses_lib.GET,
        "https://toyota-cms-media.s3.amazonaws.com/2025-sienna-01-1500x900.jpg",
        body=b"img bytes",
        headers={"content-type": "image/jpeg"},
    )

    entries = fetch_for_model("Toyota", "Sienna", 2025)
    assert len(entries) == 1
    assert entries[0]["source"] == "manufacturer"
    assert entries[0]["make"] == "Toyota"
    assert entries[0]["model"] == "Sienna"
    assert entries[0]["year"] == 2025
    assert "pressroom.toyota.com" in entries[0]["source_url"]
    assert "Toyota Motor North America" in entries[0]["attribution"]


@responses_lib.activate
def test_fetch_for_model_nissan_records_motor_trend_attribution(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.fetch_images_manufacturer.MANUFACTURER_OUT_DIR", tmp_path / "manufacturer")
    monkeypatch.setattr("scripts.fetch_images_manufacturer.IMAGES_DIR", tmp_path)

    mt_html = '<html><body><img src="https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue.jpg"/></body></html>'
    responses_lib.add(
        responses_lib.GET,
        "https://www.motortrend.com/cars/nissan/rogue/2025",
        body=mt_html,
    )
    responses_lib.add(
        responses_lib.GET,
        "https://hips.hearstapps.com/mtg-prod/2025-nissan-rogue.jpg",
        body=b"img bytes",
        headers={"content-type": "image/jpeg"},
    )

    entries = fetch_for_model("Nissan", "Rogue", 2025)
    assert len(entries) == 1
    assert "Motor Trend" in entries[0]["attribution"]
    assert entries[0]["year"] == 2025


@responses_lib.activate
def test_fetch_for_model_returns_empty_on_scrape_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.fetch_images_manufacturer.MANUFACTURER_OUT_DIR", tmp_path / "manufacturer")
    monkeypatch.setattr("scripts.fetch_images_manufacturer.IMAGES_DIR", tmp_path)

    responses_lib.add(
        responses_lib.GET,
        "https://pressroom.toyota.com/vehicle/2025-toyota-sienna/",
        status=503,
    )
    entries = fetch_for_model("Toyota", "Sienna", 2025)
    assert entries == []
