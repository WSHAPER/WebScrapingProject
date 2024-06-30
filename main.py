# main.py

import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
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
    if (element):
        return element.inner_text().strip()
    return "N/A"


def is_captcha_present(page):
    captcha_selectors = [
        "#captcha-box",  # Adjust this selector based on the actual CAPTCHA element
        "text=Please verify you are a human",  # Adjust this text based on what's shown on the CAPTCHA page
    ]
    return any(page.query_selector(selector) for selector in captcha_selectors)


def wait_for_page_load(page, timeout=60000):
    try:
        page.wait_for_load_state('networkidle', timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False


def scrape_listing(page, url):
    page.goto(url)
    if not wait_for_page_load(page):
        print("Page load timeout. Proceeding anyway.")

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

    data = {}
    for field, selector in FIELDS_TO_FETCH.items():
        try:
            element = page.query_selector(selector)
            if element:
                if field == "address":
                    data[field] = element.inner_text().replace("\n", ", ").strip()
                elif field in ["price", "nebenkosten", "heizkosten", "gesamtmiete", "kaution"]:
                    text = element.inner_text().strip()
                    data[field] = text.split()[0] if text else "N/A"
                else:
                    data[field] = element.inner_text().strip()
            else:
                data[field] = "N/A"
        except Exception as e:
            print(f"Error extracting {field}: {e}")
            data[field] = "Error"

    if data['price'] != "N/A" and data['price'] != "Error":
        try:
            data['price'] = float(data['price'].replace('€', '').replace('.', '').replace(',', '.').strip())
        except ValueError:
            print(f"Error converting price: {data['price']}")
            data['price'] = "Error"

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
                if data:
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print("Failed to scrape data.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                page.screenshot(path='error_screenshot.png')
                print("Screenshot saved as 'error_screenshot.png'")

            user_input = input("Press Enter to scrape again, or type 'q' to quit: ")
            if user_input.lower() == 'q':
                break

        browser.close()


if __name__ == "__main__":
    main()