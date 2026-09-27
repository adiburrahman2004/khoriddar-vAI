from pathlib import Path
from datetime import date, datetime
import pandas as pd
from collectors.base_collector import BaseCollector

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
EN_TO_BN = {str(i): BN_DIGITS[i] for i in range(10)}


def to_bengali_digits(text):
   return "".join(EN_TO_BN.get(char, char) for char in text)


def to_english_digits(text):
   return "".join(
      str(BN_DIGITS.index(char)) if char in BN_DIGITS else char
      for char in text
   )


class TCBCollector(BaseCollector):

   TCB_URL = "https://tcb.gov.bd/pages/daily-rmps"

   def get_latest_published_row(self):
      rows = self.page.locator("tr")
      latest_row = None
      latest_date = None

      for i in range(rows.count()):
         row = rows.nth(i)
         date_cell = row.locator('[data-column="publish_date"]')
         if date_cell.count() == 0:
               continue

         date_text = date_cell.inner_text().strip()
         if not date_text:
               continue

         try:
               published_date = datetime.strptime(
                  to_english_digits(date_text), "%d-%m-%Y"
               ).date()
         except ValueError:
               continue

         if latest_date is None or published_date > latest_date:
               latest_date = published_date
               latest_row = row

      if latest_row is None:
         self.logger.error("No valid published TCB date found on page")
         raise Exception("No valid published TCB date found")

      self.logger.info(f"Latest TCB published date: {latest_date}")
      return latest_row, latest_date

   def get_or_download_latest(self):
      self.start_browser()
      try:
         self.page.goto(self.TCB_URL)
         self.page.wait_for_selector("a.table-td-icon")

         row, published_date = self.get_latest_published_row()
         expected_file = Path("downloads") / f"tcb_{published_date.isoformat()}.xlsx"

         if expected_file.exists():
               self.logger.info(f"TCB still on {published_date}, already have it")
               return expected_file, published_date

         self.logger.info(f"New TCB report for {published_date}, downloading")
         with self.page.expect_download() as download_info:
               row.locator("a.table-td-icon").click()

         download = download_info.value
         file_bytes = Path(download.path()).read_bytes()
         file_path = self.save_file(file_bytes, "tcb", extension="xlsx", file_date=published_date)
         return file_path, published_date
      finally:
         self.close_browser()

   def parse_tcb_excel(self, file_path, published_date):
      BN_TO_EN = {
         "চাল সরু (নাজির/মিনিকেট)": "Fine Rice",
         "আলু (নতুন/পুরাতন)": "Potato",
         "পিঁয়াজ (দেশী)(নতুন/পুরাতন)": "Local Onion",
         "সয়াবিন তেল (লুজ)": "Soybean Oil (Loose)",
         "ডিম (ফার্ম)": "Farm Egg",
         "মুরগী(ব্রয়লার)": "Broiler Chicken",
         "গরু": "Beef",
      }

      df = pd.read_excel(file_path, skiprows=7, header=None)
      records = []
      seen = set()

      for _, row in df.iterrows():
         item_bn = row[0]
         unit = row[1]
         
         if pd.isna(item_bn):
               continue
         item_bn = str(item_bn).strip()

         if pd.isna(unit):
               continue
         unit = str(unit).strip()

         price_min = pd.to_numeric(row[2], errors="coerce")
         price_max = pd.to_numeric(row[3], errors="coerce")

         if pd.isna(price_min) or pd.isna(price_max):
               continue
         if price_min == 0 and price_max == 0:
               continue

         price_min = float(price_min)
         price_max = float(price_max)
         
         key = (item_bn, unit)
         if key in seen:
               self.logger.info(f"Duplicate within file, skipping: {item_bn} ({unit})")
               continue
         seen.add(key)
         
         item_en = BN_TO_EN.get(item_bn)
         if item_en is None:
               self.logger.info(f"No translation for: {item_bn}")

         records.append({
               "price_date": published_date,
               "item_bn": item_bn,
               "item_en": item_en,
               "market_name": "Dhaka (Citywide)",
               "source_name": "TCB",
               "source_type": "Government",
               "price_type": "Retail",
               "price_min": price_min,
               "price_max": price_max,
               "unit": unit,
         })

      return records

   def collect(self):
      file_path, published_date = self.get_or_download_latest()
      records = self.parse_tcb_excel(file_path, published_date)
      self.logger.info(f"Parsed {len(records)} records (published {published_date})")
      return records