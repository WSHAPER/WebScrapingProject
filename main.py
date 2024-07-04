# main.py

import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
from config import FIELDS_TO_FETCH, SEARCH_URL, BASE_URL, LIMIT_INT

BROWSER_FLAG_FILE = 'browser_running.flag'
CDP_PORT = 9222

def connect_to_browser():
    if not os.path.exists(BROWSER_FLAG_FILE):
        raise Exception("Browser flag file not found. Please run browser_manager.py first.")
    
    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
    context = browser.new_context()
    page = context.new_page()
    return playwright, browser, context, page

def safe_extract(page, selector):
    element = page.query_selector(selector)
    if element:
        return element.inner_text().strip()
    return "N/A"


def is_captcha_present(page):
    captcha_keywords = ["roboter", "human", "captcha", "verify"]
    page_text = page.inner_text('body').lower()

    if any(keyword in page_text for keyword in captcha_keywords):
        return True

    captcha_selectors = [
        "#captcha-box",
        "[id*='captcha']",  # Match any id containing 'captcha'
        "[class*='captcha']",  # Match any class containing 'captcha'
    ]
    return any(page.query_selector(selector) for selector in captcha_selectors)


def wait_for_page_load(page, timeout=60000):
    try:
        page.wait_for_load_state('networkidle', timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False

def extract_links(page):
    links = page.query_selector_all('a[data-exp-id]')
    extracted_links = []
    for link in links[:LIMIT_INT]:
        href = link.get_attribute('href')
        if href and href.startswith('/expose/'):
            full_url = f"{BASE_URL}{href}"
            extracted_links.append(full_url)
    return extracted_links

def debug_page_content(page):
    print("Current URL:", page.url)
    print("Page title:", page.title())
    print("Page content:")
    print(page.content())
    print("All links on the page:")
    all_links = page.query_selector_all('a')
    for link in all_links:
        print(link.get_attribute('href'))

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

    data = {"url": url}  # Include the URL in the data dictionary
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

    return data


def main():
    playwright = None
    browser = None
    context = None
    page = None

    try:
        playwright, browser, context, page = connect_to_browser()

        # Navigate to the search results page
        page.goto(SEARCH_URL)
        if not wait_for_page_load(page):
            print("Search results page load timeout. Proceeding anyway.")

        max_retries = 3
        for attempt in range(max_retries):
            if is_captcha_present(page):
                print("CAPTCHA detected on search page. Please solve the CAPTCHA manually.")
                input("Press Enter when you've solved the CAPTCHA...")
                page.reload()
                wait_for_page_load(page)

            # Extract links
            links = extract_links(page)
            if links:
                break
            elif attempt < max_retries - 1:
                print(f"No links found. Retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(5)  # Wait a bit before retrying
            else:
                print("No links found after all attempts. Debugging page content:")
                debug_page_content(page)

        print(f"Extracted {len(links)} links:")
        for link in links:
            print(link)

        # Scrape each listing
        all_data = []
        for link in links:
            try:
                data = scrape_listing(page, link)
                if data:
                    all_data.append(data)
                    print(f"Scraped data for {link}:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print(f"Failed to scrape data for {link}")
            except Exception as e:
                print(f"An unexpected error occurred while scraping {link}: {e}")
                page.screenshot(path=f'error_screenshot_{link.split("/")[-1]}.png')
                print(f"Screenshot saved as 'error_screenshot_{link.split('/')[-1]}.png'")

        # Save all scraped data to a JSON file
        with open('scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print("All scraped data saved to 'scraped_data.json'")

    except KeyboardInterrupt:
        print("Script execution cancelled.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Script execution finished. Browser remains open in browser_manager.py")
        if context:
            context.close()
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

if __name__ == "__main__":
    main()