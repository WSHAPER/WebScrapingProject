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
    captcha_keywords = ["roboter", "human", "captcha", "verify"]
    page_text = page.inner_text('body').lower()
    
    if any(keyword in page_text for keyword in captcha_keywords):
        return True
    
    captcha_selectors = [
        "#captcha-box",
        "[id*='captcha']",
        "[class*='captcha']",
    ]
    return any(page.query_selector(selector) for selector in captcha_selectors)

def wait_for_page_load(page, timeout=60000):
    try:
        page.wait_for_load_state('networkidle', timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False

def extract_links(page):
    links = page.query_selector_all('article[data-item="result"]')
    extracted_links = set()  # Use a set to ensure uniqueness
    for article in links:
        link_element = article.query_selector('a[data-exp-id]')
        if link_element:
            href = link_element.get_attribute('href')
            if href:
                if href.startswith('/expose/'):
                    full_url = f"{BASE_URL}{href}"
                    extracted_links.add(full_url)
                elif href.startswith('https://www.immobilienscout24.de/expose/'):
                    extracted_links.add(href)
        
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

def extract_links_stage(page):
    accept_cookies(page)

    max_retries = 3
    for attempt in range(max_retries):
        if is_captcha_present(page):
            print("CAPTCHA detected on search page. Please solve the CAPTCHA manually.")
            input("Press Enter when you've solved the CAPTCHA...")
            page.reload()
            print("Page reloaded after CAPTCHA. Waiting for 5 seconds...")
            page.wait_for_timeout(5000)  # Wait for 10 seconds after CAPTCHA
            accept_cookies(page)  # Check for cookies again after CAPTCHA

        print(f"Attempt {attempt + 1}: Waiting for search results...")
        try:
            page.wait_for_selector('article[data-item="result"]', timeout=60000)
            print("Search result articles found.")
        except PlaywrightTimeoutError:
            print("Timeout while waiting for search results. Proceeding anyway.")

        print(f"Current URL: {page.url}")
        print(f"Page title: {page.title()}")

        links = extract_links(page)
        if links:
            return links
        elif attempt < max_retries - 1:
            print(f"No links found. Retrying... (Attempt {attempt + 1}/{max_retries})")
            page.reload()
            page.wait_for_timeout(5000)  # Wait for 5 seconds before retrying
        else:
            print("No links found after all attempts. Debugging page content:")
            debug_page_content(page)
    
    return []

def scrape_data_stage(context, links):
    all_data = []
    for link in links:
        try:
            # Open a new tab for each link
            page = context.new_page()
            page.goto(link, timeout=30000)  # 30 seconds timeout
            
            if is_captcha_present(page):
                print(f"CAPTCHA detected on {link}. Please solve it manually.")
                input("Press Enter when you've solved the CAPTCHA...")
                page.reload()
            
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
        finally:
            # Close the tab after scraping
            page.close()

    return all_data

def main():
    playwright = None
    browser = None
    context = None

    try:
        playwright, browser, context, page = connect_to_browser()

        # Stage 1: Extract links
        page.goto(SEARCH_URL)
        if not wait_for_page_load(page):
            print("Search results page load timeout. Proceeding anyway.")

        links = extract_links_stage(page)
        page.close()  # Close the search results page

        print(f"\nThe following {len(links)} unique links were found:")
        for link in links:
            print(link)

        # Ask user if they want to continue with scraping
        user_input = input("\nContinue with web scraping? (y/n): ").lower().strip()
        if user_input != 'y':
            print("Scraping cancelled by user.")
            return

        # Stage 2: Scrape data
        all_data = scrape_data_stage(context, links)

        # Save all scraped data to a JSON file
        with open('scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print("All scraped data saved to 'scraped_data.json'")

    except KeyboardInterrupt:
        print("Script execution cancelled.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Script execution finished.")
        if context:
            context.close()
        if browser:
            browser.disconnect()
        if playwright:
            playwright.stop()

if __name__ == "__main__":
    main()