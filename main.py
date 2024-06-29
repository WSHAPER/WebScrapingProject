from playwright.sync_api import sync_playwright
import time
import random

def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # Navigate to Immobilienscout24 and search for apartments in Stuttgart
            page.goto("https://www.immobilienscout24.de/")
            page.fill('input[name="geocoding-location"]', "Stuttgart")
            page.click('button[data-js-click="submitSearch"]')

            # Wait for the search results to load
            page.wait_for_selector('.result-list__listing')

            apartments = []
            while len(apartments) < 150:
                # Extract apartment information
                listings = page.query_selector_all('.result-list__listing')
                for listing in listings:
                    if len(apartments) >= 150:
                        break

                    try:
                        price = listing.query_selector('.result-list-entry__primary-criterion').inner_text()
                        size = listing.query_selector('.result-list-entry__primary-criterion:nth-child(2)').inner_text()
                        rooms = listing.query_selector('.result-list-entry__primary-criterion:nth-child(3)').inner_text()
                        address = listing.query_selector('.result-list-entry__address').inner_text()

                        # You'll need to click on each listing to get more details
                        listing.click()
                        page.wait_for_selector('.is24qa-details-page')

                        # Extract additional information (floors, balcony, parking)
                        # Note: These selectors might need adjustment based on the actual page structure
                        floors = page.query_selector('.is24qa-etage').inner_text() if page.query_selector('.is24qa-etage') else "N/A"
                        balcony = "Yes" if page.query_selector('.is24qa-balkon') else "No"
                        parking = "Yes" if page.query_selector('.is24qa-stellplatz') else "No"

                        apartments.append({
                            "price": price,
                            "size": size,
                            "rooms": rooms,
                            "floors": floors,
                            "balcony": balcony,
                            "parking": parking,
                            "address": address
                        })

                        # Go back to the search results
                        page.go_back()
                        page.wait_for_selector('.result-list__listing')

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

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if 'browser' in locals():
                browser.close()

if __name__ == "__main__":
    main()