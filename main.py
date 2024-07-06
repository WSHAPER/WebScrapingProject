# main.py

import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
from config import FIELDS_TO_FETCH, BASE_URL, LIMIT_INT, SEARCH_CONFIGS
import logging
import re
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

BROWSER_FLAG_FILE = 'browser_running.flag'
CDP_PORT = 9222

def connect_to_browser():
    logging.debug("Connecting to browser")
    if not os.path.exists(BROWSER_FLAG_FILE):
        raise Exception("Browser flag file not found. Please run browser_manager.py first.")
    
    with open(BROWSER_FLAG_FILE, 'r') as f:
        port = f.read().strip().split()[-1]
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp(f"http://localhost:{port}")
    context = browser.new_context()
    logging.debug("Successfully connected to browser")
    return playwright, browser, context

def safe_extract(page, selector):
    element = page.query_selector(selector)
    if element:
        return element.inner_text().strip()
    return "N/A"

def is_cookie_consent_present(page):
    consent_selectors = [
        "#uc-fading-wrapper",
        "[data-testid='uc-header-wrapper']",
        "text=Wir verwenden Cookies",
        "button:has-text('Alle akzeptieren')"
    ]
    return any(page.query_selector(selector) for selector in consent_selectors)

def accept_cookies(page):
    if is_cookie_consent_present(page):
        try:
            accept_button = page.query_selector("button:has-text('Alle akzeptieren')")
            if accept_button:
                accept_button.click()
                print("Cookies accepted automatically.")
                page.wait_for_load_state('networkidle')
            else:
                print("Accept button not found. Cookie consent may require manual interaction.")
        except Exception as e:
            print(f"Error accepting cookies: {e}")


def is_captcha_present(page):
    # Check for visible CAPTCHA elements
    visible_captcha_selectors = [
        ".g-recaptcha",  # Common class for reCAPTCHA
        "iframe[src*='google.com/recaptcha']",  # reCAPTCHA iframe
        "#captcha-box",  # Custom CAPTCHA element
        "[id*='captcha']:not([style*='display: none'])",  # Any visible element with 'captcha' in its ID
    ]

    for selector in visible_captcha_selectors:
        element = page.query_selector(selector)
        if element and element.is_visible():
            return True

    # Check for CAPTCHA-related text in the page content
    captcha_keywords = ["captcha", "verify you're not a robot", "human verification"]
    page_text = page.inner_text('body').lower()

    if any(keyword in page_text for keyword in captcha_keywords):
        # Additional check: Is this text actually visible?
        for keyword in captcha_keywords:
            elements = page.query_selector_all(f"text=/{keyword}/i")
            for element in elements:
                if element.is_visible():
                    return True

    return False

def wait_for_page_load(page, timeout=60000):
    try:
        page.wait_for_load_state('networkidle', timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False


def is_valid_address(address):
    # Check if the address contains a street name or number
    return ',' in address and any(char.isdigit() for char in address.split(',')[0])


def extract_links(page, has_parking, has_balcony):
    links = page.query_selector_all('article[data-item="result"]')
    extracted_links = set()  # Use a set to ensure uniqueness
    for article in links:
        link_element = article.query_selector('a[data-exp-id]')
        address_element = article.query_selector('button.result-list-entry__map-link')

        if link_element and address_element:
            href = link_element.get_attribute('href')
            address = address_element.inner_text().strip()

            if href and is_valid_address(address):
                if href.startswith('/expose/'):
                    full_url = f"{BASE_URL}{href}"
                    # Associate parking and balcony info with the link here
                    extracted_links.add((full_url, has_parking, has_balcony))
                elif href.startswith('https://www.immobilienscout24.de/expose/'):
                    # Associate parking and balcony info with the link here
                    extracted_links.add((href, has_parking, has_balcony))

        if len(extracted_links) >= LIMIT_INT:
            break

    return list(extracted_links)[:LIMIT_INT]

def debug_page_content(page):
    print("Current URL:", page.url)
    print("Page title:", page.title())
    print("All article elements:")
    articles = page.query_selector_all('article[data-item="result"]')
    for i, article in enumerate(articles):
        print(f"Article {i + 1}:")
        link_element = article.query_selector('a[data-exp-id]')
        if link_element:
            print(f"  Link: {link_element.get_attribute('href')}")
        else:
            print("  No link found in this article")
    print("\nFull page content:")
    print(page.content())

def scrape_listing(page, url):
    page.goto(url)
    if not wait_for_page_load(page):
        print(f"Page load timeout for {url}. Proceeding anyway.")

    if is_captcha_present(page):
        print("CAPTCHA detected. Please solve the CAPTCHA manually.")
        input("Press Enter when you've solved the CAPTCHA...")
        page.reload()
        if not wait_for_page_load(page):
            print("Page reload timeout after CAPTCHA. Proceeding anyway.")

    # Wait for the title to appear, with a timeout
    try:
        page.wait_for_selector("#expose-title", timeout=30000)
    except PlaywrightTimeoutError:
        print("Timeout while waiting for #expose-title. The page might not have loaded correctly.")
        page.screenshot(path='error_screenshot.png')
        print("Screenshot saved as 'error_screenshot.png'")
        return None

    data = {"url": url}
    for field, selector in FIELDS_TO_FETCH.items():
        try:
            element = page.query_selector(selector)
            if element:
                if field == "address":
                    address = element.inner_text().replace("\n", ", ").strip()
                    # Remove any duplicate commas and extra spaces
                    address = ", ".join(part.strip() for part in address.split(",") if part.strip())
                    data[field] = address
                elif field == "heating_expenses_excluded":
                    heizkosten_text = element.inner_text().strip().lower()
                    data[field] = "nicht in nebenkosten enthalten" in heizkosten_text
                    if data[field]:
                        data['heating_costs'] = None
                    else:
                        # Extract numeric value if present
                        numeric_value = ''.join(filter(lambda x: x.isdigit() or x in [',', '.'], heizkosten_text))
                        data['heating_costs'] = numeric_value if numeric_value else None
                elif field in ["price", "additional_costs", "total_rent", "deposit"]:
                    text = element.inner_text().strip()
                    # Remove any non-numeric characters except , and .
                    numeric_value = ''.join(filter(lambda x: x.isdigit() or x in [',', '.'], text))
                    data[field] = numeric_value if numeric_value else None
                    if field == "total_rent":
                        data["total_rent_estimated"] = "~" in text
                elif field == "stories":
                    stories_text = element.inner_text().strip()
                    if "von" in stories_text:
                        story, total_stories = stories_text.split("von")
                        data["story"] = story.strip()
                        data["total_stories"] = total_stories.strip()
                    else:
                        data["story"] = stories_text
                        data["total_stories"] = None
                else:
                    data[field] = element.inner_text().strip()
            else:
                data[field] = None
        except Exception as e:
            print(f"Error extracting {field} from {url}: {e}")
            data[field] = "Error"

    # Convert price and other numeric fields to float
    for field in ["price", "additional_costs", "total_rent", "deposit", "heating_costs"]:
        if field in data and data[field] not in [None, "Error"]:
            try:
                data[field] = float(data[field].replace('.', '').replace(',', '.'))
            except ValueError:
                print(f"Error converting {field}: {data[field]}")
                data[field] = None

    # Convert story and total_stories to integers if possible
    for field in ["story", "total_stories"]:
        if data.get(field) and data[field] != "Error":
            try:
                data[field] = int(data[field])
            except ValueError:
                print(f"Could not convert {field} to integer: {data[field]}")

    # Check if the listing should be skipped based on the "stories" field
    if data.get("story") is None or data.get("total_stories") is None:
        print(f"Skipping listing {url} due to invalid 'stories' field: {data.get('stories')}")
        return None

    return data

def scrape_data_stage(context, links_with_info):
    all_data = []
    for link, has_parking, has_balcony in links_with_info:
        try:
            page = context.new_page()
            page.goto(link, timeout=30000)

            if is_captcha_present(page):
                print(f"CAPTCHA detected on {link}. Please solve it manually.")
                input("Press Enter when you've solved the CAPTCHA...")
                page.reload()

            data = scrape_listing(page, link)
            if data:
                # Add parking and balcony info to the scraped data
                data['parking'] = has_parking
                data['balcony'] = has_balcony
                all_data.append(data)
                print(f"Scraped data for {link}:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"Skipped or failed to scrape data for {link}")
        except Exception as e:
            print(f"An unexpected error occurred while scraping {link}: {e}")
            page.screenshot(path=f'error_screenshot_{link.split("/")[-1]}.png')
            print(f"Screenshot saved as 'error_screenshot_{link.split('/')[-1]}.png'")
        finally:
            page.close()

    return all_data


def extract_links_for_config(page, base_url, start_page=1):
    all_links = []
    current_page = start_page
    wait_time = 5000  # Wait time in milliseconds (5 seconds)

    # Parse the base_url to get the search parameters
    parsed_url = urlparse(base_url)
    query_params = parse_qs(parsed_url.query)
    equipment = query_params.get('equipment', [])
    has_parking = 'parking' in equipment
    has_balcony = 'balcony' in equipment

    while len(all_links) < LIMIT_INT:
        page_url = f"{base_url}&pagenumber={current_page}" if '?' in base_url else f"{base_url}?pagenumber={current_page}"

        print(f"Navigating to page {current_page}: {page_url}")
        try:
            page.goto(page_url, wait_until="networkidle", timeout=60000)
            print(f"Waiting for {wait_time / 1000} seconds for the page to settle...")
            page.wait_for_timeout(wait_time)

            if is_captcha_present(page):
                print(f"CAPTCHA detected on search page {current_page}. Please solve the CAPTCHA manually.")
                input("Press Enter when you've solved the CAPTCHA...")
                page.reload(wait_until="networkidle", timeout=60000)
                print("Page reloaded after CAPTCHA. Waiting for 5 seconds...")
                page.wait_for_timeout(wait_time)
                accept_cookies(page)

            print(f"Extracting links from page {current_page}...")
            page.wait_for_selector('article[data-item="result"]', timeout=60000)
            print("Search result articles found.")

            links = extract_links(page, has_parking, has_balcony)  # Pass the parameters here
            all_links.extend(links)
            print(f"Found {len(links)} links on page {current_page}. Total links: {len(all_links)}")

            if not links:
                print("No more results found. Stopping pagination.")
                break

        except PlaywrightTimeoutError as e:
            print(f"Timeout error on page {current_page}: {e}")
            print("Attempting to proceed to the next page...")
        except Exception as e:
            print(f"An error occurred on page {current_page}: {e}")
            print("Attempting to proceed to the next page...")

        current_page += 1

    return all_links[:LIMIT_INT]

def main():
    logging.debug("Starting main function")
    playwright = None
    browser = None
    context = None
    search_page = None

    try:
        playwright, browser, context = connect_to_browser()
        search_page = context.new_page()

        all_unique_links = set()

        for config in SEARCH_CONFIGS:
            print(f"\nExtracting links for configuration: {config}")
            try:
                links_with_info = extract_links_for_config(search_page, config)
                new_links = set(links_with_info) - all_unique_links
                all_unique_links.update(new_links)
                print(f"Found {len(new_links)} new unique links for this configuration.")
                print(f"Total unique links so far: {len(all_unique_links)}")
            except Exception as e:
                print(f"An error occurred while processing configuration {config}: {e}")
                print("Proceeding to the next configuration...")

        links_list = list(all_unique_links)
        print(f"\nTotal {len(links_list)} unique links found across all configurations:")
        for link, has_parking, has_balcony in links_list:
            print(f"{link} (Parking: {has_parking}, Balcony: {has_balcony})")

        # Ask user if they want to continue with scraping
        user_input = input("\nContinue with web scraping? (y/n): ").lower().strip()
        if user_input != 'y':
            print("Scraping cancelled by user.")
            return

        # Stage 2: Scrape data
        all_data = scrape_data_stage(context, links_list)

        # Save all scraped data to a JSON file
        with open('scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print("All scraped data saved to 'scraped_data.json'")

    except KeyboardInterrupt:
        print("Script execution cancelled.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if search_page:
            print(f"Current URL when error occurred: {search_page.url}")
            search_page.screenshot(path='error_screenshot.png')
            print("Screenshot saved as 'error_screenshot.png'")
    finally:
        print("Script execution finished.")
        if search_page:
            search_page.close()
        if context:
            logging.debug("Closing context")
            context.close()
        
        print("Browser remains open. You can continue using it or close it manually when you're done.")
        
        # Keep the script running until user decides to close
        while True:
            user_input = input("Enter 'q' to quit and close the browser connection, or press Enter to keep it open: ")
            if user_input.lower() == 'q':
                if browser:
                    logging.debug("Disconnecting browser")
                    browser.disconnect()
                if playwright:
                    logging.debug("Stopping playwright")
                    playwright.stop()
                print("Browser connection closed.")
                break
            else:
                print("Browser connection remains open. You can run the script again to continue scraping.")

if __name__ == "__main__":
    main()