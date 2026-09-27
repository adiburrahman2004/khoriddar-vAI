from collectors.tcb_collector import TCBCollector
from database.db import save_prices

c = TCBCollector("tcb")
records = c.collect()

print(f"{len(records)} records parsed")
print(records[:3])

seen = set()
for r in records:
   key = (r["price_date"], r["item_bn"], r["unit"], r["market_name"], r["source_name"], r["price_type"])
   if key in seen:
      print("DUPLICATE IN BATCH:", key)
   seen.add(key)
inserted, skipped = save_prices(records)
print(f"Inserted: {inserted}, Skipped: {skipped}")