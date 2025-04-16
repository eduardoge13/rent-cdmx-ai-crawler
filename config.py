# config.py

BASE_URL = "https://www.inmuebles24.com/departamentos-en-renta-en-ciudad-de-mexico"
CSS_SELECTOR = "[class^='postingCard-module__posting-top']"
REQUIRED_KEYS = [
    "Address",
    "Price",
    "Rooms",
    "Neighborhood",
    "City_Province",
    "Square_foot_units_square_meters",
    "Commodities",
]