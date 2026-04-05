import json
from pathlib import Path
from unittest.mock import patch
import pytest
import responses as responses_lib

from scripts.fetch_images_manufacturer import (
    get_model_url,
    extract_og_images,
    extract_json_ld_images,
    extract_gallery_images,
    scrape_model_images,
    download_image,
    fetch_for_model,
)
from bs4 import BeautifulSoup


# --- get_model_url ---

def test_get_model_url_toyota():
    url = get_model_url("Toyota", "Sienna")
    assert url == "https://www.toyota.com/sienna/"


def test_get_model_url_nissan():
    url = get_model_url("Nissan", "Rogue")
    assert url == "https://www.nissanusa.com/vehicles/rogue/"


def test_get_model_url_mercedes():
    url = get_model_url("Mercedes-Benz", "GLC")
    assert url == "https://www.mbusa.com/en/vehicles/class/glc/overview.html"


def test_get_model_url_lincoln():
    url = get_model_url("Lincoln", "Navigator")
    assert url == "https://www.lincoln.com/vehicles/navigator/"


def test_get_model_url_unknown_model():
    url = get_model_url("Toyota", "UnknownModel")
    assert url is None


# --- extract_og_images ---

def test_extract_og_images():
    html = """
    <html><head>
      <meta property="og:image" content="https://example.com/car.jpg"/>
      <meta property="twitter:image" content="https://example.com/car2.jpg"/>
    </head></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_og_images(soup, "https://example.com")
    assert "https://example.com/car.jpg" in urls
    assert "https://example.com/car2.jpg" in urls


def test_extract_og_images_skips_non_http():
    html = """
    <html><head>
      <meta property="og:image" content="/relative/path.jpg"/>
    </head></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_og_images(soup, "https://example.com")
    assert urls == []


# --- extract_json_ld_images ---

def test_extract_json_ld_images_single():
    data = {"@type": "Car", "image": "https://example.com/car.jpg"}
    html = f'<script type="application/ld+json">{json.dumps(data)}</script>'
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_json_ld_images(soup)
    assert "https://example.com/car.jpg" in urls


def test_extract_json_ld_images_list():
    data = {"@type": "Car", "image": ["https://example.com/a.jpg", "https://example.com/b.jpg"]}
    html = f'<script type="application/ld+json">{json.dumps(data)}</script>'
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_json_ld_images(soup)
    assert len(urls) == 2


def test_extract_json_ld_images_invalid_json():
    html = '<script type="application/ld+json">not valid json</script>'
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_json_ld_images(soup)
    assert urls == []


# --- extract_gallery_images ---

def test_extract_gallery_images_basic():
    html = """
    <html><body>
      <img src="https://example.com/car_gallery.jpg" width="1200"/>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_gallery_images(soup, "https://example.com")
    assert "https://example.com/car_gallery.jpg" in urls


def test_extract_gallery_images_skips_logos():
    html = """
    <html><body>
      <img src="https://example.com/toyota_logo.png"/>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_gallery_images(soup, "https://example.com")
    assert urls == []


def test_extract_gallery_images_skips_small():
    html = """
    <html><body>
      <img src="https://example.com/thumbnail.jpg" width="50"/>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_gallery_images(soup, "https://example.com")
    assert urls == []


def test_extract_gallery_images_resolves_protocol_relative():
    html = '<img src="//example.com/car.jpg"/>'
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_gallery_images(soup, "https://example.com")
    assert "https://example.com/car.jpg" in urls


def test_extract_gallery_images_resolves_root_relative():
    html = '<img src="/images/car.jpg"/>'
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_gallery_images(soup, "https://toyota.com/sienna")
    assert "https://toyota.com/images/car.jpg" in urls


# --- download_image ---

@responses_lib.activate
def test_download_image_success(tmp_path):
    responses_lib.add(
        responses_lib.GET,
        "https://www.toyota.com/car.jpg",
        body=b"fake image bytes",
        headers={"content-type": "image/jpeg"},
    )
    dest = tmp_path / "car.jpg"
    assert download_image("https://www.toyota.com/car.jpg", dest) is True
    assert dest.read_bytes() == b"fake image bytes"


@responses_lib.activate
def test_download_image_skips_non_image(tmp_path):
    responses_lib.add(
        responses_lib.GET,
        "https://www.toyota.com/page.html",
        body=b"<html></html>",
        headers={"content-type": "text/html"},
    )
    dest = tmp_path / "page.html"
    assert download_image("https://www.toyota.com/page.html", dest) is False
    assert not dest.exists()


# --- scrape_model_images ---

@responses_lib.activate
def test_scrape_model_images_returns_urls():
    html = """
    <html><head>
      <meta property="og:image" content="https://www.toyota.com/sienna_exterior.jpg"/>
    </head><body></body></html>
    """
    responses_lib.add(
        responses_lib.GET,
        "https://www.toyota.com/sienna/",
        body=html,
    )
    urls = scrape_model_images("Toyota", "Sienna")
    assert "https://www.toyota.com/sienna_exterior.jpg" in urls


@responses_lib.activate
def test_scrape_model_images_returns_empty_on_fetch_failure():
    responses_lib.add(
        responses_lib.GET,
        "https://www.toyota.com/sienna/",
        status=503,
    )
    urls = scrape_model_images("Toyota", "Sienna")
    assert urls == []


def test_scrape_model_images_unknown_model():
    urls = scrape_model_images("Toyota", "Unknown")
    assert urls == []


# --- fetch_for_model ---

@responses_lib.activate
def test_fetch_for_model_downloads_and_records(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.fetch_images_manufacturer.MANUFACTURER_OUT_DIR", tmp_path / "manufacturer")
    monkeypatch.setattr("scripts.fetch_images_manufacturer.IMAGES_DIR", tmp_path)

    html = '<html><head><meta property="og:image" content="https://www.toyota.com/sienna.jpg"/></head></html>'
    responses_lib.add(responses_lib.GET, "https://www.toyota.com/sienna/", body=html)
    responses_lib.add(
        responses_lib.GET,
        "https://www.toyota.com/sienna.jpg",
        body=b"img bytes",
        headers={"content-type": "image/jpeg"},
    )

    entries = fetch_for_model("Toyota", "Sienna", 2025)
    assert len(entries) == 1
    assert entries[0]["source"] == "manufacturer"
    assert entries[0]["make"] == "Toyota"
    assert entries[0]["model"] == "Sienna"


@responses_lib.activate
def test_fetch_for_model_returns_empty_on_scrape_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.fetch_images_manufacturer.MANUFACTURER_OUT_DIR", tmp_path / "manufacturer")
    monkeypatch.setattr("scripts.fetch_images_manufacturer.IMAGES_DIR", tmp_path)

    responses_lib.add(responses_lib.GET, "https://www.toyota.com/sienna/", status=503)
    entries = fetch_for_model("Toyota", "Sienna", 2025)
    assert entries == []
