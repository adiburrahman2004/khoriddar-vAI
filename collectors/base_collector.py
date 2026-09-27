import logging
from pathlib import Path
from datetime import date
from playwright.sync_api import sync_playwright


class BaseCollector:
    def __init__(self, name):
        self.name = name
        self.playwright = None
        self.browser = None
        self.page = None

        Path("logs").mkdir(exist_ok=True)

        logging.basicConfig(
            filename="logs/collector.log",
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(name)

    def start_browser(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        return self.browser, self.page

    def close_browser(self):
        try:
            if self.browser:
                self.browser.close()
        finally:
            if self.playwright:
                self.playwright.stop()

    def save_file(self, source_bytes, filename_prefix, extension="xlsx", file_date=None):
        downloads = Path("downloads")
        downloads.mkdir(exist_ok=True)
        file_date = file_date or date.today()
        filename = downloads / f"{filename_prefix}_{file_date.isoformat()}.{extension}"
        with open(filename, "wb") as f:
            f.write(source_bytes)
        self.logger.info(f"Saved file: {filename}")
        return filename