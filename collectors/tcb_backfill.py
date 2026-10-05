from pathlib import Path
from datetime import date, datetime

import pandas as pd

from collectors.base_collector import BaseCollector
from collectors.tcb_collector import to_english_digits


# TODO: item_bn for backfill rows uses rough umbrella terms, not verified official Bangla.
# Revisit once Items table / proper translation layer exists.
BACKFILL_EN_TO_BN = {
    "Broad Rice": "চাল (মোটা)",
    "Rice-(Fine)": "চাল (সরু)",
    "Atta": "আটা",
    "Refined Soyabean oil": "সয়াবিন তেল",
    "Palm Oil (loose)": "পাম তেল",
    "M.Dal (Red Lentil)": "মসুর ডাল",
    "Gram": "ছোলা",
    "Sugar": "চিনি",
    "Potato": "আলু",
    "Onion": "পেঁয়াজ",
    "Garlic": "রসুন",
    "Turmeric": "হলুদ",
    "Dry Chili": "শুকনা মরিচ",
    "Ginger": "আদা",
    "Salt": "লবণ",
}

# Verified against the live file's "Unit Price : KG/LTR-TAKA" header + product type.
BACKFILL_UNITS = {
    "Broad Rice": "KG", "Rice-(Fine)": "KG", "Atta": "KG",
    "Refined Soyabean oil": "LTR", "Palm Oil (loose)": "LTR",
    "M.Dal (Red Lentil)": "KG", "Gram": "KG", "Sugar": "KG",
    "Potato": "KG", "Onion": "KG", "Garlic": "KG",
    "Turmeric": "KG", "Dry Chili": "KG", "Ginger": "KG", "Salt": "KG",
}


class TCBBackfillCollector(BaseCollector):

    TCB_URL = "https://tcb.gov.bd/pages/last30-rmps"

    def get_backfill_rows(self):
        rows = self.page.locator("tr")
        results = []

        for i in range(rows.count()):
            row = rows.nth(i)
            date_cell = row.locator('[data-column="publish_date"]')
            file_link = row.locator('a.table-td-icon')

            if date_cell.count() == 0 or file_link.count() == 0:
                continue

            date_text = date_cell.inner_text().strip()

            try:
                published_date = datetime.strptime(
                    to_english_digits(date_text), "%d-%m-%Y"
                ).date()
            except ValueError:
                self.logger.warning(f"Could not parse backfill date: {date_text}")
                continue

            results.append((published_date, row))

        results.sort(key=lambda x: x[0], reverse=True)
        self.logger.info(f"Found {len(results)} TCB backfill reports")
        return results

    def find_and_download(self):
        self.start_browser()
        try:
            self.page.goto(self.TCB_URL)
            self.page.wait_for_selector("a.table-td-icon")

            backfill_rows = self.get_backfill_rows()
            downloaded_files = []

            for published_date, row in backfill_rows:
                expected_file = Path("downloads") / f"tcb_backfill_{published_date.isoformat()}.xlsx"

                if expected_file.exists():
                    self.logger.info(f"Already downloaded TCB backfill: {published_date}")
                    downloaded_files.append((expected_file, published_date))
                    continue

                self.logger.info(f"Downloading TCB backfill: {published_date}")
                with self.page.expect_download() as download_info:
                    row.locator("a.table-td-icon").click()

                download = download_info.value
                file_bytes = Path(download.path()).read_bytes()
                file_path = self.save_file(file_bytes, "tcb_backfill", extension="xlsx", file_date=published_date)
                downloaded_files.append((file_path, published_date))

            return downloaded_files
        finally:
            self.close_browser()

    def parse_tcb_excel(self, file_path):
        df = pd.read_excel(file_path, header=None)
        records = []

        headers = df.iloc[3].tolist()
        item_columns = {}

        for column_index, item_en in enumerate(headers[1:], start=1):
            if pd.isna(item_en):
                continue
            item_en = str(item_en).strip()
            if item_en not in BACKFILL_EN_TO_BN:
                self.logger.info(f"No Bangla translation for backfill item: {item_en}")
                continue
            item_columns[column_index] = item_en

        for _, row in df.iloc[4:].iterrows():
            raw_date = row.iloc[0]

            if pd.isna(raw_date):
                continue

            # Excel gives real datetime objects here, not strings — confirmed by inspection.
            try:
                price_date = raw_date.date()
            except AttributeError:
                self.logger.warning(f"Skipped unparseable backfill date: {raw_date!r}")
                continue

            for column_index, item_en in item_columns.items():
                value = row.iloc[column_index]

                if pd.isna(value):
                    continue
                value = str(value).strip()

                try:
                    price_min, price_max = value.split("-", 1)
                    price_min = float(price_min.strip())
                    price_max = float(price_max.strip())
                except ValueError:
                    self.logger.warning(f"Skipped malformed price for {item_en} on {price_date}: {value}")
                    continue

                records.append({
                    "price_date": price_date,
                    "item_bn": BACKFILL_EN_TO_BN[item_en],
                    "item_en": item_en,
                    "market_name": "Dhaka (Citywide)",
                    "source_name": "TCB",
                    "source_type": "Government",
                    "price_type": "Retail",
                    "price_min": price_min,
                    "price_max": price_max,
                    "unit": BACKFILL_UNITS[item_en],
                })

        self.logger.info(f"Parsed {len(records)} backfill records from {file_path}")
        return records

    def collect(self):
        files = self.find_and_download()
        all_records = []

        for file_path, published_date in files:
            records = self.parse_tcb_excel(file_path)
            all_records.extend(records)
            self.logger.info(f"Processed backfill report published {published_date}")

        self.logger.info(f"Total backfill records collected: {len(all_records)}")
        return all_records
     
if __name__ == "__main__":
    c = TCBBackfillCollector("tcb_backfill")
    records = c.collect()
    print(len(records), "total records")
    print(records[:3])