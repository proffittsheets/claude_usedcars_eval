from pathlib import Path

# --- Paths ---
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANUAL_DIR = DATA_DIR / "manual"
IMAGES_DIR = RAW_DIR / "images"

# --- Vehicle scope ---
MODEL_YEARS = [2021, 2022, 2023, 2024, 2025]

TARGET_MODELS = {
    "Toyota": ["RAV4", "Highlander", "Sienna", "Venza", "4Runner", "Sequoia", "Camry"],
    "Nissan": ["Pathfinder", "Murano", "Armada", "Rogue", "Altima"],
    "Mercedes-Benz": ["GLC", "GLE", "GLS", "C-Class"],
    "Lincoln": ["Corsair", "Nautilus", "Aviator", "Navigator"],
}

# fueleconomy.gov uses different model name prefixes for some models.
# Maps (make, model) -> prefix to use when querying /vehicle/menu/model.
FUEL_ECONOMY_MODEL_PREFIXES = {
    ("Mercedes-Benz", "C-Class"): "C3",  # API uses "C300", "C300 4matic", etc.
}

BODY_TYPES = ["Sedan", "SUV", "Minivan"]

MAX_MSRP = 80_000

PRICE_TIERS = {
    "low":    (0,      40_000),
    "medium": (40_000, 60_000),
    "high":   (60_000, 80_000),
}

# --- API base URLs ---
FUEL_ECONOMY_BASE = "https://www.fueleconomy.gov/ws/rest"
NHTSA_BASE = "https://api.nhtsa.gov/SafetyRatings"
CARQUERY_BASE = "https://www.carqueryapi.com/api/0.3/"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

# --- Rate limiting (seconds between requests) ---
FUEL_ECONOMY_DELAY = 0.5
NHTSA_DELAY = 0.5
CARQUERY_DELAY = 1.0
WIKIMEDIA_DELAY = 0.5
MANUFACTURER_DELAY = 2.0


def get_price_tier(msrp: int) -> str:
    for tier, (low, high) in PRICE_TIERS.items():
        if low <= msrp < high:
            return tier
    return "high"  # anything at exactly 80k
