import json
from pathlib import Path
import pytest
import responses as responses_lib

from scripts.fetch_images_wikimedia import (
    search_commons,
    get_image_info,
    is_suitable_image,
    download_image,
    fetch_for_model,
)
from scripts.config import WIKIMEDIA_API


SAMPLE_SEARCH_RESPONSE = {
    "query": {
        "search": [
            {"title": "File:2024 Toyota Sienna XSE.jpg", "ns": 6},
            {"title": "File:2024 Toyota Sienna interior.jpg", "ns": 6},
        ]
    }
}

SAMPLE_IMAGEINFO_RESPONSE = {
    "query": {
        "pages": {
            "12345": {
                "title": "File:2024 Toyota Sienna XSE.jpg",
                "imageinfo": [
                    {
                        "url": "https://upload.wikimedia.org/wikipedia/commons/sienna.jpg",
                        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/sienna.jpg",
                        "width": 1600,
                        "height": 900,
                        "extmetadata": {
                            "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            "Artist": {"value": "John Doe"},
                            "DescriptionUrl": {"value": "https://commons.wikimedia.org/wiki/File:2024_Toyota_Sienna_XSE.jpg"},
                        },
                    }
                ],
            }
        }
    }
}


@responses_lib.activate
def test_search_commons_returns_titles():
    responses_lib.add(
        responses_lib.GET,
        WIKIMEDIA_API,
        json=SAMPLE_SEARCH_RESPONSE,
    )
    titles = search_commons("2024 Toyota Sienna")
    assert "File:2024 Toyota Sienna XSE.jpg" in titles


@responses_lib.activate
def test_search_commons_returns_empty_on_error():
    responses_lib.add(
        responses_lib.GET,
        WIKIMEDIA_API,
        status=500,
    )
    titles = search_commons("2024 Toyota Sienna")
    assert titles == []


@responses_lib.activate
def test_get_image_info_returns_records():
    responses_lib.add(
        responses_lib.GET,
        WIKIMEDIA_API,
        json=SAMPLE_IMAGEINFO_RESPONSE,
    )
    titles = ["File:2024 Toyota Sienna XSE.jpg"]
    results = get_image_info(titles)
    assert len(results) == 1
    assert results[0]["license"] == "CC BY-SA 4.0"
    assert results[0]["width"] == 1600


@responses_lib.activate
def test_get_image_info_returns_empty_on_error():
    responses_lib.add(
        responses_lib.GET,
        WIKIMEDIA_API,
        status=500,
    )
    results = get_image_info(["File:Test.jpg"])
    assert results == []


def test_get_image_info_empty_titles():
    results = get_image_info([])
    assert results == []


@pytest.mark.parametrize("info,expected", [
    ({"title": "File:2024 Toyota Sienna.jpg", "width": 1600, "height": 900}, True),
    ({"title": "File:Toyota logo.png", "width": 200, "height": 200}, False),
    ({"title": "File:Toyota badge.jpg", "width": 800, "height": 600}, False),
    ({"title": "File:Toyota Sienna diagram.png", "width": 1200, "height": 900}, False),
    # Portrait orientation (too tall)
    ({"title": "File:Sienna photo.jpg", "width": 400, "height": 800}, False),
])
def test_is_suitable_image(info, expected):
    assert is_suitable_image(info) == expected


@responses_lib.activate
def test_download_image(tmp_path):
    responses_lib.add(
        responses_lib.GET,
        "https://upload.wikimedia.org/test.jpg",
        body=b"fake image bytes",
    )
    dest = tmp_path / "test.jpg"
    success = download_image("https://upload.wikimedia.org/test.jpg", dest)
    assert success is True
    assert dest.exists()
    assert dest.read_bytes() == b"fake image bytes"


@responses_lib.activate
def test_download_image_returns_false_on_error(tmp_path):
    responses_lib.add(
        responses_lib.GET,
        "https://upload.wikimedia.org/missing.jpg",
        status=404,
    )
    dest = tmp_path / "missing.jpg"
    success = download_image("https://upload.wikimedia.org/missing.jpg", dest)
    assert success is False
    assert not dest.exists()


@responses_lib.activate
def test_fetch_for_model_downloads_images(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "scripts.fetch_images_wikimedia.WIKIMEDIA_OUT_DIR",
        tmp_path / "wikimedia",
    )
    monkeypatch.setattr(
        "scripts.fetch_images_wikimedia.IMAGES_DIR",
        tmp_path,
    )

    # Search response
    responses_lib.add(responses_lib.GET, WIKIMEDIA_API, json=SAMPLE_SEARCH_RESPONSE)
    # Imageinfo response
    responses_lib.add(responses_lib.GET, WIKIMEDIA_API, json=SAMPLE_IMAGEINFO_RESPONSE)
    # Image download — uses thumb_url, not full url
    responses_lib.add(
        responses_lib.GET,
        "https://upload.wikimedia.org/wikipedia/commons/thumb/sienna.jpg",
        body=b"fake image",
    )

    entries = fetch_for_model("Toyota", "Sienna", 2024)
    assert len(entries) == 1
    assert entries[0]["source"] == "wikimedia"
    assert entries[0]["license"] == "CC BY-SA 4.0"
    assert entries[0]["make"] == "Toyota"


@responses_lib.activate
def test_fetch_for_model_returns_empty_when_no_results(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "scripts.fetch_images_wikimedia.WIKIMEDIA_OUT_DIR",
        tmp_path / "wikimedia",
    )
    responses_lib.add(
        responses_lib.GET,
        WIKIMEDIA_API,
        json={"query": {"search": []}},
    )
    entries = fetch_for_model("Toyota", "Nonexistent", 2024)
    assert entries == []
