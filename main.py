from playwright.sync_api import sync_playwright
import time
import random
import json
import os
from urllib.parse import urljoin


def load_cookies(context):
    if os.path.exists('cookies.json'):
        with open('cookies.json', 'r') as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print("Cookies loaded successfully.")
    else:
        print("No saved cookies found.")


def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()

            # Load pre-accepted cookies
            load_cookies(context)

            page = context.new_page()

            # Navigate to Immobilienscout24 and search for apartments in Stuttgart
            base_url = "https://www.immobilienscout24.de"
            search_url = f"{base_url}/Suche/de/baden-wuerttemberg/stuttgart/wohnung-mieten?enteredFrom=one_step_search"
            page.goto(search_url)

            # Wait for the search results to load
            page.wait_for_selector('.result-list__listing')

            apartments = []
            while len(apartments) < 150:
                # Extract apartment information for individual listings
                listings = page.query_selector_all('a[data-exp-id]')
                for listing in listings:
                    if len(apartments) >= 150:
                        break

                    try:
                        # Extract the title and URL of the listing
                        title = listing.query_selector('h2').inner_text()
                        url = listing.get_attribute('href')

                        # Construct the full URL correctly
                        full_url = urljoin(base_url, url)

                        # Navigate to the listing page
                        listing_page = context.new_page()
                        listing_page.goto(full_url)
                        listing_page.wait_for_load_state('networkidle')

                        # Extract detailed information
                        price = listing_page.query_selector(
                            '[data-cy="price"] span').inner_text() if listing_page.query_selector(
                            '[data-cy="price"] span') else "N/A"
                        size = listing_page.query_selector(
                            '[data-cy="totalArea"] span').inner_text() if listing_page.query_selector(
                            '[data-cy="totalArea"] span') else "N/A"
                        rooms = listing_page.query_selector(
                            '[data-cy="no-of-rooms"] span').inner_text() if listing_page.query_selector(
                            '[data-cy="no-of-rooms"] span') else "N/A"
                        address = listing_page.query_selector(
                            '[data-cy="is24qa-objektanschrift"]').inner_text() if listing_page.query_selector(
                            '[data-cy="is24qa-objektanschrift"]') else "N/A"
                        floors = listing_page.query_selector(
                            '[data-cy="floor"] span').inner_text() if listing_page.query_selector(
                            '[data-cy="floor"] span') else "N/A"
                        balcony = "Yes" if listing_page.query_selector('[data-cy="balcony-terrace"] span') else "No"
                        parking = "Yes" if listing_page.query_selector('[data-cy="parking"] span') else "No"

                        apartments.append({
                            "title": title,
                            "url": full_url,
                            "price": price,
                            "size": size,
                            "rooms": rooms,
                            "floors": floors,
                            "balcony": balcony,
                            "parking": parking,
                            "address": address
                        })

                        listing_page.close()

                    except Exception as e:
                        print(f"Error processing listing: {e}")
                        continue

                    # Add a random delay between 1 and 3 seconds
                    time.sleep(random.uniform(1, 3))

                # Check if there's a next page and navigate to it
                next_button = page.query_selector('a[data-nav-next-page]')
                if next_button:
                    next_button.click()
                    page.wait_for_selector('.result-list__listing')
                else:
                    break

            # Print the collected data
            for apartment in apartments:
                print(apartment)

            # Save the data to a JSON file
            with open('apartments.json', 'w', encoding='utf-8') as f:
                json.dump(apartments, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if 'browser' in locals():
                browser.close()


if __name__ == "__main__":
    main()