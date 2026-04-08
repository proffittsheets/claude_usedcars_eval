# Image Fetch Plan

## Current State (as of 2026-04-05)

Year scope: **2024, 2025, 2026**. All 2021–2023 raw data and images cleared.

`fetch_images_manufacturer.py` is being rewritten to use year-specific sources.
`fetch_images_wikimedia.py` is the fallback for any model/year with no manufacturer source.

---

## Image Sources by Brand

### Toyota
**Source:** Toyota Pressroom (`pressroom.toyota.com`)
**URL pattern:** `https://pressroom.toyota.com/vehicle/{year}-toyota-{slug}/`
**Strategy:** Scrape S3 press images from `toyota-cms-media.s3.amazonaws.com`
**Coverage:** 2024 ✓, 2025 ✓, 2026 ✓ (all models except Venza 2025/2026 — 404)
**Notes:**
- 100+ images per page, deduplicate by base filename (strip size suffixes like `-1500x900`)
- Filter to largest available size per unique image
- Venza falls back to Wikimedia for 2025/2026

**Model slugs:**
- RAV4 → `rav4`
- Highlander → `highlander`
- Sienna → `sienna`
- Venza → `venza` (2024 only; 2025/2026 fall back to Wikimedia)
- 4Runner → `4runner`
- Sequoia → `sequoia`
- Camry → `camry`

---

### Nissan
**Source:** Motor Trend (`motortrend.com`)
**URL pattern:** `https://www.motortrend.com/cars/nissan/{slug}/{year}`
**Strategy:** Scrape `hips.hearstapps.com/mtg-prod/` CDN image URLs
**Coverage:** 2024 ✓, 2025 ✓ (2026 likely redirects to current)
**Notes:**
- Filenames include year (e.g. `2025-nissan-rogue-front-view.jpg`) — genuinely year-specific
- ~12-13 images per page

**Model slugs:**
- Pathfinder → `pathfinder`
- Murano → `murano`
- Armada → `armada`
- Rogue → `rogue`
- Altima → `altima`

---

### Mercedes-Benz
**Source:** Motor Trend (`motortrend.com`)
**URL pattern:** `https://www.motortrend.com/cars/mercedes-benz/{slug}/{year}`
**Strategy:** Same as Nissan — scrape `mtg-prod` CDN images
**Coverage:** 2024 ✓, 2025 ✓

**Model slugs:**
- GLC → `glc-class`
- GLE → `gle-class`
- GLS → `gls`
- C-Class → `c-class`

---

### Lincoln
**Source:** Motor Trend (`motortrend.com`)
**URL pattern:** `https://www.motortrend.com/cars/lincoln/{slug}/{year}`
**Strategy:** Same as Nissan/Mercedes
**Coverage:** 2024 ✓, 2025 ✓

**Model slugs:**
- Corsair → `corsair`
- Nautilus → `nautilus`
- Aviator → `aviator`
- Navigator → `navigator`

---

## Fallback Chain

For any model/year where the primary source returns 0 images or 404:
1. Try the brand's primary source without year (current model page)
2. Fall back to Wikimedia (already working, year-specific)

---

## Changes Needed in `fetch_images_manufacturer.py`

1. **Toyota**: Replace page scraper with Toyota Pressroom scraper
   - New function: `scrape_toyota_pressroom(model_slug, year)` → scrape S3 URLs, deduplicate by base name, prefer largest size
   - `MODEL_URL_SLUGS["Toyota"]` maps to pressroom slugs

2. **Nissan / Mercedes-Benz / Lincoln**: Add Motor Trend scraper
   - New function: `scrape_motor_trend(brand_slug, model_slug, year)` → scrape `mtg-prod` CDN URLs
   - Filter: only `hips.hearstapps.com/mtg-prod/` URLs, skip anything with wrong brand in filename
   - `MODEL_URL_SLUGS` updated with MT slugs per brand

3. **`get_model_url`**: Replaced by `scrape_model_images(make, model, year)` dispatching per brand

4. **Manifest**: Each entry tagged with `source_url` = the page scraped, `original_url` = CDN URL, `year` = actual year

---

## Changes Needed in `fetch_images_wikimedia.py`

- Already working with 2-second delay and `max_retries=5` for downloads
- Uses `thumb_url` (1200px) instead of full-res — 429s handled correctly
- No changes needed; just re-run for 2024/2025/2026 after manufacturer fetch completes

---

## Tests to Update

`tests/test_fetch_images_manufacturer.py`:
- Replace `test_get_model_url_*` tests with tests for new per-brand scrape functions
- Add Motor Trend mock response fixtures
- Add Toyota Pressroom mock response fixtures

---

## Run Order After Implementation

```bash
python3 -m scripts.fetch_fuel_economy        # 2024/2025/2026 data
python3 -m scripts.fetch_nhtsa_safety         # 2024/2025/2026 data
python3 -m scripts.fetch_images_manufacturer  # Toyota pressroom + Motor Trend
python3 -m scripts.fetch_images_wikimedia     # fallback for gaps
python3 -m scripts.generate_compare_images    # review compare_images.html
python3 -m scripts.build_catalog              # merge all data
python3 build.py                              # render site
```

CarQuery is currently down — skip for now. Catalog builds fine without it (body type and seat count will be null).
