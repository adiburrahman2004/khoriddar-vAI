import sys
sys.stdout.reconfigure(encoding="utf-8")
from collectors.tcb_collector import TCBCollector
from database.db import save_prices


def main():
   collector = TCBCollector("tcb")
   records = collector.collect()
   inserted, skipped = save_prices(records)
   collector.logger.info(
      f"TCB pipeline complete: {len(records)} parsed, {inserted} inserted, {skipped} skipped"
   )


if __name__ == "__main__":
   main()