# main.py

from playwright.sync_api import sync_playwright
import time
import json
import os
from config import FIELDS_TO_FETCH, TARGET_URL


def load_cookies(context):
    if os.path.exists('cookies.json'):
        with open('cookies.json', 'r') as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print("Cookies loaded successfully.")
    else:
        print("No saved cookies found.")


def safe_extract(page, selector):
    element = page.query_selector(selector)
    if element:
        return element.inner_text().strip()
    return "N/A"


def scrape_listing(page, url):
    page.goto(url)
    page.wait_for_load_state('networkidle')
    time.sleep(2)  # Wait an additional 2 seconds for any dynamic content

    data = {}
    for field, selector in FIELDS_TO_FETCH.items():
        data[field] = safe_extract(page, selector)

    # Special handling for price (removing "€" symbol and converting to float)
    if data['price'] != "N/A":
        data['price'] = float(data['price'].replace('€', '').replace('.', '').replace(',', '.').strip())

    return data


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        load_cookies(context)
        page = context.new_page()

        while True:
            try:
                data = scrape_listing(page, TARGET_URL)
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"An error occurred: {e}")

            user_input = input("Press Enter to scrape again, or type 'q' to quit: ")
            if user_input.lower() == 'q':
                break

        browser.close()


if __name__ == "__main__":
    main()