from playwright.sync_api import sync_playwright
import json

def save_cookies(context):
    cookies = context.cookies()
    with open('cookies.json', 'w') as f:
        json.dump(cookies, f)
    print("Cookies saved successfully.")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to Immobilienscout24
        page.goto("https://www.immobilienscout24.de")

        print("Please manually accept the cookie terms in the browser window.")
        input("Press Enter when you have accepted the terms...")

        # Save the cookies
        save_cookies(context)

        browser.close()

if __name__ == "__main__":
    main()