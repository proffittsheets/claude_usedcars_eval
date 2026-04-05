import json
import pytest


# --- fueleconomy.gov XML fixtures ---

@pytest.fixture
def sample_fuel_economy_model_xml():
    """XML response from /vehicle/menu/model listing model names."""
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<menuItems>
  <menuItem><text>Sienna AWD</text><value>Sienna AWD</value></menuItem>
  <menuItem><text>Sienna FWD</text><value>Sienna FWD</value></menuItem>
  <menuItem><text>RAV4</text><value>RAV4</value></menuItem>
</menuItems>"""


@pytest.fixture
def sample_fuel_economy_options_xml():
    """XML response from /vehicle/menu/options listing vehicle IDs."""
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<menuItems>
  <menuItem><text>Toyota Sienna AWD (trim 1)</text><value>48751</value></menuItem>
  <menuItem><text>Toyota Sienna AWD (trim 2)</text><value>48752</value></menuItem>
</menuItems>"""


@pytest.fixture
def sample_fuel_economy_record_xml():
    """XML response from /vehicle/{id}."""
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<vehicle>
  <id>48751</id>
  <year>2024</year>
  <make>Toyota</make>
  <model>Sienna</model>
  <trany>Automatic (variable gear ratios)</trany>
  <drive>All-Wheel Drive</drive>
  <fuelType1>Regular Gasoline</fuelType1>
  <atvType>Hybrid</atvType>
  <city08>36</city08>
  <highway08>36</highway08>
  <comb08>36</comb08>
  <cityA08>0</cityA08>
  <highwayA08>0</highwayA08>
  <combA08>0</combA08>
  <fuelCost08>1150</fuelCost08>
</vehicle>"""


# Legacy dict fixture kept for build_catalog tests
@pytest.fixture
def sample_fuel_economy_options():
    return {
        "menuItem": [
            {"value": "48751", "text": "Toyota Sienna FWD"},
            {"value": "48752", "text": "Toyota Sienna AWD"},
        ]
    }


@pytest.fixture
def sample_fuel_economy_record():
    return {
        "id": 48751,
        "year": 2024,
        "make": "Toyota",
        "model": "Sienna",
        "trany": "Automatic (variable gear ratios)",
        "drive": "Front-Wheel Drive",
        "fuelType1": "Regular Gasoline",
        "atvType": "Hybrid",
        "city08": 36,
        "highway08": 36,
        "comb08": 36,
        "cityA08": 0,
        "highwayA08": 0,
        "combA08": 0,
        "fuelCost08": 1150,
    }


# --- NHTSA fixtures ---

@pytest.fixture
def sample_nhtsa_models():
    return {
        "Results": [
            {"VehicleId": 19217, "VehicleDescription": "2024 Toyota Sienna FWD"},
            {"VehicleId": 19218, "VehicleDescription": "2024 Toyota Sienna AWD"},
        ]
    }


@pytest.fixture
def sample_nhtsa_ratings():
    return {
        "Results": [
            {
                "VehicleId": 19217,
                "OverallRating": "5",
                "OverallFrontCrashRating": "5",
                "OverallSideCrashRating": "5",
                "RolloverRating": "4",
                "NHTSAForwardCollisionWarning": "Standard",
                "NHTSALaneDepartureWarning": "Standard",
            }
        ]
    }


# --- CarQuery fixture ---

@pytest.fixture
def sample_carquery_response():
    models = {
        "Trims": [
            {
                "model_id": "51423",
                "model_make_id": "toyota",
                "model_name": "Sienna",
                "model_trim": "XSE AWD",
                "model_year": "2024",
                "model_body": "Minivan",
                "model_engine_position": "Front",
                "model_doors": "5",
                "model_seats": "8",
                "model_drive": "AWD",
                "model_transmission_type": "Automatic",
                "model_lkm_hwy": "9.8",
                "model_lkm_city": "9.8",
                "model_sold_in_us": "1",
                "model_msrp": "40000",
            }
        ]
    }
    return f"?({json.dumps(models)});"
