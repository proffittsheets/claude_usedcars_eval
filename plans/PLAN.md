# Car Vision Board Website — Phase 1 Plan

## Context

Molly & Justin Sheets are planning to buy a used car in ~2 years and want a bespoke website to help them research and downselect on makes, models, and features. This is Phase 1: a static site showing new/recent cars (2021–2025) from preferred brands (Toyota, Nissan, Mercedes, Lincoln) with full specs, imagery, safety ratings, and pricing—so they can narrow down what they actually want before hunting used inventory.

The repo at `/Users/molly/Repos/claude_usedcars_eval` is currently empty (just the vision doc and README). Everything needs to be built from scratch.

---

## Architecture Decision

**Python-driven static site** — Python data scripts feed structured JSON into Jinja2 templates, producing plain HTML/CSS/JS output in a `site/` directory.

- No Node.js, no React/Vue, no build tooling
- Output files can be opened locally in a browser right now
- Aligns with future S3 + GitHub Actions hosting goal
- Single language stack (Python) for both data and site generation

---

## Directory Structure

```
claude_usedcars_eval/
├── data/
│   ├── sources.md                  # Data source registry (maintained as scripts are written)
│   ├── raw/
│   │   ├── nhtsa_safety/           # Raw NHTSA API responses
│   │   ├── fuel_economy/           # Raw fueleconomy.gov responses
│   │   ├── carquery/               # Raw CarQuery API responses
│   │   └── images/
│       ├── wikimedia/          # Images fetched via Wikimedia Commons API
│       ├── manufacturer/       # Images scraped from brand media/press pages
│       └── manifest.json       # Source URLs, licenses, fetch method per image
│   ├── processed/
│   │   └── catalog.json            # Master merged vehicle catalog
│   └── manual/
│       ├── msrp_seed.json          # Hand-entered base MSRP from manufacturer sites
│       ├── iihs_overrides.json     # IIHS TSP/TSP+ status (no public API)
│       ├── color_options.json      # Color options per make/model/year
│       └── details_overrides.json  # Cup holders, heated seats, audio system
├── scripts/
│   ├── config.py                   # Brands, models, year range, price tiers, paths
│   ├── utils.py                    # HTTP retry, rate limiting, logging helpers
│   ├── fetch_fuel_economy.py       # fueleconomy.gov — MPG, hybrid flag
│   ├── fetch_nhtsa_safety.py       # NHTSA 5-Star ratings
│   ├── fetch_carquery_specs.py     # Body type, drivetrain, seats (JSONP)
│   ├── fetch_images_wikimedia.py   # Images from Wikimedia Commons API (no auth)
│   ├── fetch_images_manufacturer.py# Images scraped from brand media/press pages
│   ├── fetch_msrp.py               # Merges CarQuery MSRP with manual seed
│   └── build_catalog.py            # ETL: joins all raw data → catalog.json
├── tests/
│   ├── conftest.py                 # Fixtures, mock API responses
│   ├── test_fetch_nhtsa.py
│   ├── test_fetch_fuel_economy.py
│   ├── test_fetch_carquery.py
│   ├── test_fetch_images_wikimedia.py
│   ├── test_fetch_images_manufacturer.py
│   ├── test_build_catalog.py
│   └── test_schema.py              # Validates catalog.json schema invariants
├── templates/
│   ├── base.html                   # Layout: nav, footer, CSS/JS includes
│   ├── index.html                  # Homepage: all brands, price tier tabs, filters
│   ├── brand.html                  # Per-brand page with model cards
│   ├── car_card.html               # Reusable card macro
│   └── car_detail.html             # Full detail: gallery, specs, ratings, accordion
├── static/
│   ├── css/
│   │   ├── main.css
│   │   ├── gallery.css
│   │   └── cards.css
│   └── js/
│       ├── gallery.js              # Lightbox + scroll (vanilla JS)
│       ├── filters.js              # Client-side card filtering
│       └── dropdown.js             # Accordion for minor details
├── site/                           # Build output — gitignored
├── build.py                        # Site renderer: catalog.json → HTML via Jinja2
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
└── .github/workflows/deploy.yml    # Stub for future S3 deployment
```

---

## Vehicle Scope (Phase 1)

**Years:** 2021–2025 | **Max MSRP:** $80,000 | **Requirements:** AWD option, family-focused

| Brand | Models |
|-------|--------|
| Toyota | RAV4, Highlander, Sienna, Venza, 4Runner, Sequoia, Camry AWD |
| Nissan | Pathfinder, Murano, Armada, Rogue, Altima AWD |
| Mercedes | GLC, GLE, GLS, C-Class (4MATIC trims only) |
| Lincoln | Corsair, Nautilus, Aviator, Navigator |

**Price tiers** (defined in `scripts/config.py`):
- Low: < $40,000
- Medium: $40,000–$60,000
- High: $60,000–$80,000

---

## Data Sources

All sources documented in `data/sources.md` as scripts are written.

| Data | Source | Auth |
|------|--------|------|
| Vehicle specs (body, drivetrain, seats) | CarQuery API — `https://www.carqueryapi.com/api/0.3/` | None |
| MPG + hybrid flag | FuelEconomy.gov — `https://www.fueleconomy.gov/ws/rest/` | None |
| NHTSA 5-star safety | `https://api.nhtsa.gov/SafetyRatings/` | None |
| IIHS TSP/TSP+ | `https://www.iihs.org/ratings/top-safety-picks` | Manual (no API) |
| Images (option A) | Wikimedia Commons API — `https://commons.wikimedia.org/w/api.php` | None |
| Images (option B) | Manufacturer press/media pages — scraped per brand | None |
| MSRP | Manual seed from manufacturer sites + CarQuery where available | None |

**Notes:**
- CarQuery returns JSONP — strip wrapper: `json.loads(text.split('(',1)[1].rsplit(')',1)[0])`
- NHTSA requires a 2-step call: model list → VehicleId list → ratings per VehicleId
- Both image scripts run independently, storing results in `data/raw/images/wikimedia/` and `data/raw/images/manufacturer/` respectively
- A `compare_images.html` page is generated showing both sources side by side per model so quality and coverage can be evaluated before committing to one approach
- Final image source selected after review; `build_catalog.py` configured to use the chosen source
- `manifest.json` tracks source URL, license, and fetch method per image

**Manufacturer scrape targets:**
- Toyota: toyota.com model pages
- Nissan: nissanusa.com model pages
- Mercedes: mbusa.com model pages
- Lincoln: lincoln.com model pages

---

## catalog.json Schema (per vehicle entry)

```json
{
  "id": "toyota-sienna-2024-xse-awd",
  "make": "Toyota", "model": "Sienna", "year": 2024, "trim": "XSE AWD",
  "body_type": "Minivan",
  "has_awd": true,
  "is_hybrid": true,
  "price_tier": "medium",
  "msrp_usd": 42085,
  "seats": 8,
  "mpg_city": 36, "mpg_highway": 36, "mpg_combined": 36,
  "fuel_type": "Hybrid",
  "color_options": ["Midnight Black Metallic", "Blueprint"],
  "safety": {
    "nhtsa_overall": 5, "nhtsa_front_crash": 5, "nhtsa_side_crash": 5,
    "iihs_overall": "Top Safety Pick+",
    "source_url": "https://api.nhtsa.gov/SafetyRatings/..."
  },
  "details": {
    "cup_holders": 12,
    "heated_seats": "front and second row",
    "audio_system": "JBL 12-speaker premium"
  },
  "images": {
    "exterior": ["images/cars/toyota/sienna/2024/exterior_01.jpg"],
    "interior": ["images/cars/toyota/sienna/2024/interior_01.jpg"]
  },
  "source_urls": {
    "manufacturer": "https://www.toyota.com/sienna",
    "fuel_economy": "https://www.fueleconomy.gov/...",
    "nhtsa_safety": "https://api.nhtsa.gov/..."
  }
}
```

---

## Website Pages

| Page | Template | Description |
|------|----------|-------------|
| `index.html` | `index.html` | All brands, price tier tabs, filter controls (hybrid, body type, brand) |
| `{brand}.html` | `brand.html` | Per-brand model cards grouped by tier |
| `cars/{id}.html` | `car_detail.html` | Full detail: exterior + interior gallery (scroll + lightbox), specs, NHTSA stars, IIHS badge, accordion for minor details |

**Key UI components:**
- Car card: hero image, hybrid badge, tier badge, MSRP, MPG, seat count, NHTSA stars, "View Details" link
- Gallery: horizontal scroll strip + click-to-fullscreen lightbox (vanilla JS)
- Filter bar: client-side JS using `data-*` attributes — no page reload
- Accordion: "Additional Details" collapsed by default, reveals cup holders / heated seats / audio

---

## Build Sequence

1. **Project scaffolding** — `.gitignore`, `requirements.txt`, `scripts/config.py`, `scripts/utils.py`
2. **Fetch scripts + tests** (write each test alongside its script):
   - `fetch_fuel_economy.py` + `test_fetch_fuel_economy.py`
   - `fetch_nhtsa_safety.py` + `test_fetch_nhtsa.py`
   - `fetch_carquery_specs.py` + `test_fetch_carquery.py`
   - `fetch_images_wikimedia.py` + `test_fetch_images_wikimedia.py`
   - `fetch_images_manufacturer.py` + `test_fetch_images_manufacturer.py`
   - Generate `compare_images.html` to evaluate both sources side by side — **pick winner before proceeding**
3. **Manual data files** — `data/manual/msrp_seed.json`, `iihs_overrides.json`, `color_options.json`, `details_overrides.json`
4. **`build_catalog.py`** + `test_build_catalog.py` + `test_schema.py`
5. **HTML templates** — `base.html` → `index.html` → `brand.html` → `car_card.html` → `car_detail.html`
6. **`build.py`** (site renderer)
7. **CSS + JS** — `main.css`, `gallery.js`, `filters.js`, `dropdown.js`
8. **GitHub Actions stub** — `.github/workflows/deploy.yml` (manual trigger only for now)
9. **Finalize `data/sources.md`**

---

## Testing

`pytest` + `responses` library for HTTP mocking.

Key invariants enforced by `tests/test_schema.py`:
- All entries have `has_awd: true`
- `year` in 2021–2025
- `msrp_usd` ≤ 80,000
- `price_tier` in `["low", "medium", "high"]`
- Required fields present: `id`, `make`, `model`, `year`, `body_type`, `msrp_usd`

---

## Verification

End-to-end test:
1. Run `pip install -r requirements.txt`
2. Run each `fetch_*.py` script — check `data/raw/` populated (images pre-populated manually)
3. Run `python scripts/build_catalog.py` — check `data/processed/catalog.json` has entries
4. Run `pytest` — all tests pass
5. Run `python build.py` — check `site/` directory generated
6. Open `site/index.html` in browser — verify cards render, filters work, gallery opens
7. Open a car detail page — verify gallery, lightbox, accordion all function

---

## Critical Files

- [scripts/config.py](scripts/config.py) — Created first; everything else imports from here
- [scripts/build_catalog.py](scripts/build_catalog.py) — ETL merge; correctness of entire data layer
- [build.py](build.py) — Bridge between data and frontend
- [data/sources.md](data/sources.md) — Audit trail for all external data sources
- [tests/test_schema.py](tests/test_schema.py) — Contract/invariant tests for the full pipeline
