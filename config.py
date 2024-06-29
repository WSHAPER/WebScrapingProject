# config.py

FIELDS_TO_FETCH = {
    "title": ".is24qa-expose-title",
    "price": ".is24qa-kaltmiete",
    "size": ".is24qa-flaeche-ca",
    "rooms": ".is24qa-zimmer",
    "address": ".address-block",
    "nebenkosten": ".is24qa-nebenkosten",
    "heizkosten": ".is24qa-heizkosten",
    "gesamtmiete": ".is24qa-gesamtmiete",
    "kaution": ".is24qa-kaution-o-genossenschaftsanteile"
}

# URL to scrape
TARGET_URL = "https://www.immobilienscout24.de/expose/150993085#/"