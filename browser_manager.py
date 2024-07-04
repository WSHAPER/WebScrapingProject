# browser_manager.py

from playwright.sync_api import sync_playwright
import json
import os
import atexit

BROWSER_FLAG_FILE = 'browser_running.flag'
CDP_PORT = 9222


def load_cookies(context):
    if os.path.exists('cookies.json'):
        with open('cookies.json', 'r') as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print("Cookies loaded successfully.")
    else:
        print("No saved cookies found.")


def launch_browser():
    global playwright, browser
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False, args=[
        f'--remote-debugging-port={CDP_PORT}',
        '--no-sandbox',
        '--disable-setuid-sandbox'
    ])
    context = browser.new_context()
    load_cookies(context)
    page = context.new_page()

    # Create a flag file to indicate the browser is running
    with open(BROWSER_FLAG_FILE, 'w') as f:
        f.write(f'running on port {CDP_PORT}')

    print(f"Browser launched with CDP on port {CDP_PORT}. Flag file created: {BROWSER_FLAG_FILE}")
    return playwright, browser, context, page


def close_browser():
    if 'browser' in globals():
        browser.close()
    if 'playwright' in globals():
        playwright.stop()
    if os.path.exists(BROWSER_FLAG_FILE):
        os.remove(BROWSER_FLAG_FILE)
    print("Browser closed and flag file removed.")


def manage_browser():
    global playwright, browser
    playwright, browser, _, _ = launch_browser()
    print(f"Browser launched with CDP enabled on port {CDP_PORT}. You can now run your main script.")
    print("To close the browser, enter 'q' and press Enter.")

    while True:
        user_input = input("Enter 'q' to quit and close the browser, or press Enter to keep it open: ")
        if user_input.lower() == 'q':
            break

    close_browser()


# Ensure browser is closed when the script exits
atexit.register(close_browser)

if __name__ == "__main__":
    manage_browser()