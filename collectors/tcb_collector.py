from pathlib import Path
from datetime import date
import pandas as pd
from collectors.base_collector import BaseCollector 

EN_TO_BN = {
   "0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪",
   "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯",
}


def to_bengali_digits(text):
   return "".join(EN_TO_BN.get(char, char) for char in text)


class TCBCollector(BaseCollector):

   TCB_URL = "https://tcb.gov.bd/pages/daily-rmps"

   def already_downloaded_today(self):
      expected_file = Path("downloads") / f"tcb_{date.today().isoformat()}.xlsx"
      return expected_file.exists(), expected_file

   def find_and_download(self):
      self.start_browser()
      try:
         self.page.goto(self.TCB_URL)
         self.page.wait_for_selector("a.table-td-icon")

         today_bn = to_bengali_digits(date.today().strftime("%d-%m-%Y"))
         row = self.page.locator("tr").filter(has_text=today_bn)

         if row.count() == 0:
               self.logger.error(f"No TCB file found for {today_bn}")
               raise Exception(f"No TCB file found for {today_bn}")

         if row.count() > 1:
               self.logger.warning(f"Multiple rows found for {today_bn}. Using first match.")
               row = row.first

         with self.page.expect_download() as download_info:
               row.locator("a.table-td-icon").click()

         download = download_info.value
         file_bytes = Path(download.path()).read_bytes()

         return self.save_file(file_bytes, "tcb", extension="xlsx")
      finally:
         self.close_browser()

   def parse_tcb_excel(self, file_path):
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

      for _, row in df.iterrows():
         item_bn = row[0]
         unit = row[1]

         if pd.isna(item_bn):
               self.logger.info("Skipped empty/header row")
               continue
         item_bn = str(item_bn).strip()

         if pd.isna(unit):
               self.logger.info(f"Skipped section header: {item_bn}")
               continue
         unit = str(unit).strip()

         price_min = pd.to_numeric(row[2], errors="coerce")
         price_max = pd.to_numeric(row[3], errors="coerce")

         if pd.isna(price_min) or pd.isna(price_max):
               self.logger.info(f"Skipped invalid price: {item_bn}")
               continue
         if price_min == 0 and price_max == 0:
               self.logger.info(f"Skipped zero-price item: {item_bn}")
               continue

         price_min = float(price_min)
         price_max = float(price_max)

         item_en = BN_TO_EN.get(item_bn)
         if item_en is None:
               self.logger.info(f"No translation for: {item_bn}")

         records.append({
               "price_date": date.today(),
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
      exists, file_path = self.already_downloaded_today()

      if exists:
         self.logger.info(f"Already downloaded today: {file_path}")
      else:
         file_path = self.find_and_download()

      records = self.parse_tcb_excel(file_path)
      self.logger.info(f"Parsed {len(records)} records from TCB")
      return records
   
if __name__ == "__main__":
   c = TCBCollector("tcb")
   records = c.collect()
   print(len(records), "records")
   print(records[:3])