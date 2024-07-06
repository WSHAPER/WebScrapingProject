# config.py

FIELDS_TO_FETCH = {
    "title": "#expose-title",
    "price": ".is24qa-kaltmiete",
    "size": ".is24qa-flaeche-main",
    "rooms": ".is24qa-zimmer",
    "stories": ".is24qa-etage",
    "address": ".address-block",
    "additional_costs": ".is24qa-nebenkosten",
    "heating_expenses_excluded": ".is24qa-heizkosten",
    "total_rent": ".is24qa-warmmiete-main, .is24qa-geschaetzte-warmmiete-main",
    "deposit": ".is24qa-kaution-o-genossenschaftsanteile"
}

# Search configurations
SEARCH_CONFIGS = [
    "https://www.immobilienscout24.de/Suche/de/baden-wuerttemberg/stuttgart/wohnung-mieten?equipment=parking,balcony",
    "https://www.immobilienscout24.de/Suche/de/baden-wuerttemberg/stuttgart/wohnung-mieten?equipment=balcony",
    "https://www.immobilienscout24.de/Suche/de/baden-wuerttemberg/stuttgart/wohnung-mieten?equipment=parking",
    "https://www.immobilienscout24.de/Suche/de/baden-wuerttemberg/stuttgart/wohnung-mieten"
]

# Base URL for individual listings
BASE_URL = "https://www.immobilienscout24.de"

# Limit for the number of listings to scrape
LIMIT_INT = 150