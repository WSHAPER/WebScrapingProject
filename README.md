# Immobilienscout24 Listing Scraper

This project is a web scraper designed to extract information from Immobilienscout24 property listings. It uses Playwright for browser automation and handles cookie management for seamless operation.

## Features

- Scrapes detailed information from Immobilienscout24 property listings
- Handles cookie management to maintain session
- Provides CAPTCHA detection and manual solving option
- Supports repeated scraping of the same listing for monitoring changes

## Prerequisites

- Python 3.10.11 (tested version)
- pip (Python package installer)

## Project Structure

```
WebScrapingProject/
├── .idea/
├── venv/
├── __pycache__/
├── config.py
├── cookie-saver.py
├── main.py
├── requirements.txt
└── cookies.json (generated after running cookie-saver.py)
```

## Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd WebScrapingProject
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

5. Install Playwright browsers:
   ```
   playwright install
   ```

## Usage

1. First, run the cookie-saver script to set up your session:
   ```
   python cookie-saver.py
   ```
   Follow the prompts to manually accept cookie terms in the browser window.

2. Update the `TARGET_URL` in `config.py` with the Immobilienscout24 listing URL you want to scrape.

3. Run the main scraper:
   ```
   python main.py
   ```

4. The script will scrape the listing and display the results. Press Enter to scrape again or 'q' to quit.

## Configuration

You can modify the `FIELDS_TO_FETCH` dictionary in `config.py` to adjust which fields are scraped from the listing.

## Troubleshooting

- If you encounter a CAPTCHA, the script will pause and allow you to solve it manually.
- In case of errors, the script will save a screenshot as 'error_screenshot.png' for debugging.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

## Disclaimer

This scraper is for educational purposes only. Always respect the terms of service of the websites you interact with.