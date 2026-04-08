# Car Vision Board — Sheets Family

A personal research website for comparing new and recent vehicles as part of a long-term car buying decision. Built as a static site generated from Python data pipelines.

**View site:** open `site/index.html` in a browser after local generation. 
TO DO: Will host after some local bug fixes.

---

## What It Does

- **81 vehicles** across 6 brands and model years 2024–2026
- Per-vehicle pages with photo gallery, full specs, safety ratings, and color options
- Featured car carousel on the homepage (auto-scrolling)
- Filter by brand, body type (SUV / Sedan / Minivan), price tier, and hybrid status
- NHTSA 5-star crash ratings and IIHS Top Safety Pick status on every card
- Hybrid badge on vehicles with hybrid/PHEV powertrain options
- Light and dark mode with OS preference detection and manual toggle
- All data sourced from public APIs and manufacturer press materials

**Brands covered:** Toyota · Nissan · Mercedes-Benz · Lincoln · Honda · Volkswagen

---

## Project Structure

```
claude_usedcars_eval/
├── data/
│   ├── raw/
│   │   ├── fuel_economy/       # MPG data from fueleconomy.gov
│   │   ├── nhtsa_safety/       # NHTSA 5-star crash rating API responses
│   │   ├── carquery/           # CarQuery trim/spec API responses
│   │   └── images/
│   │       ├── manufacturer/   # Press images scraped from Toyota Pressroom + Motor Trend
│   │       ├── wikimedia/      # Fallback images from Wikimedia Commons
│   │       └── manifest.json   # Source URL, license, and attribution per image
│   ├── processed/
│   │   └── catalog.json        # Master vehicle catalog (generated — do not edit directly)
│   └── manual/
│       ├── msrp_seed.json      # Base MSRP by make/model/year (update annually)
│       ├── iihs_overrides.json # IIHS TSP / TSP+ ratings (no public API)
│       ├── body_types.json     # Body type by make/model (SUV / Sedan / Minivan)
│       ├── color_options.json  # Exterior color options by make/model
│       └── details_overrides.json # Cup holders, heated seats, audio system
├── scripts/
│   ├── config.py                   # Brands, models, year range, price tiers, file paths
│   ├── fetch_fuel_economy.py       # Fetches MPG + hybrid flag from fueleconomy.gov
│   ├── fetch_nhtsa_safety.py       # Fetches crash ratings from NHTSA API
│   ├── fetch_carquery_specs.py     # Fetches body type + drivetrain from CarQuery
│   ├── fetch_images_manufacturer.py # Scrapes press images (Toyota Pressroom + Motor Trend)
│   ├── fetch_images_wikimedia.py   # Fetches images from Wikimedia Commons
│   └── build_catalog.py            # Merges all data sources → catalog.json
├── templates/                  # Jinja2 HTML templates
├── static/css/                 # Stylesheets (main.css, cards.css, gallery.css)
├── static/js/                  # Vanilla JS (theme.js, filters.js, carousel.js, gallery.js)
├── site/                       # Build output — open index.html here (gitignored)
├── build.py                    # Renders catalog.json + templates → site/
└── requirements.txt
```

---

## Setup

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for running tests
```

---

## Running the Build

To regenerate the site after any data or template changes:

```bash
python3 build.py
```

Then open `site/index.html` in a browser.

---

## Data Pipeline

Run these in order to fully refresh all data from scratch. In practice you only need to re-run the specific scripts whose data has changed.

```bash
# 1. Fetch MPG and hybrid status
python3 -m scripts.fetch_fuel_economy

# 2. Fetch NHTSA crash ratings
python3 -m scripts.fetch_nhtsa_safety

# 3. Fetch CarQuery specs (body type, drivetrain) — may be unavailable, see note below
python3 -m scripts.fetch_carquery_specs

# 4. Fetch manufacturer press images (Toyota Pressroom + Motor Trend CDN)
python3 -m scripts.fetch_images_manufacturer

# 5. Fetch Wikimedia fallback images (used for VW ID.4 and any gaps)
python3 -m scripts.fetch_images_wikimedia

# 6. Merge all sources into catalog.json
python3 -m scripts.build_catalog

# 7. Render HTML
python3 build.py
```

> **Note on CarQuery:** The CarQuery API has been intermittently unavailable. Body types are handled by `data/manual/body_types.json` as a fallback, so the site functions correctly without it.

---

## Adding a New Vehicle Model

1. **`scripts/config.py`** — add the model to `TARGET_MODELS` under its brand
2. **`data/manual/msrp_seed.json`** — add base MSRP for each year
3. **`data/manual/iihs_overrides.json`** — add IIHS rating (TSP or TSP+)
4. **`data/manual/body_types.json`** — add body type (SUV, Sedan, or Minivan)
5. **`data/manual/color_options.json`** — add available exterior colors
6. **`data/manual/details_overrides.json`** — add cup holders, heated seats, audio (optional)
7. **`fetch_images_manufacturer.py`** — add Motor Trend or Toyota Pressroom slug
8. Re-run the data pipeline and `build.py`

## Adding a New Brand

Same as above, plus:
- Add a nav link in `templates/base.html`
- `build.py` will auto-generate a `{brand-slug}.html` brand page

---

## Updating Data Annually

| What | File | How |
|---|---|---|
| New model year | `scripts/config.py` | Add year to `MODEL_YEARS` |
| MSRP | `data/manual/msrp_seed.json` | Add new year key per model |
| IIHS ratings | `data/manual/iihs_overrides.json` | Check iihs.org/ratings/top-safety-picks |
| MPG / hybrid | Re-run `fetch_fuel_economy.py` | New year data auto-populates |
| NHTSA ratings | Re-run `fetch_nhtsa_safety.py` | New year data auto-populates |
| Images | Re-run `fetch_images_manufacturer.py` | Skips models already on disk |

---

## Running Tests

```bash
pytest
```

---

## Image Sources & Attribution

- **Toyota**: Toyota Motor North America Pressroom (pressroom.toyota.com)
- **Nissan, Mercedes-Benz, Lincoln, Honda, Volkswagen**: Motor Trend / Hearst Autos editorial pages
- **Fallback**: Wikimedia Commons (used for VW ID.4 and any models not covered above)

All images are used for personal research only. See `site/sources.html` for full attributions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data | Python 3, requests, BeautifulSoup4 |
| Templating | Jinja2 |
| Frontend | Vanilla HTML/CSS/JS — no frameworks, no build tools |
| Data APIs | fueleconomy.gov, NHTSA, CarQuery, Wikimedia Commons |
| Hosting (future) | GitHub Actions → S3 static hosting |
