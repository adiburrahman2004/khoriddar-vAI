from collectors.tcb_backfill import TCBBackfillCollector
from database.db import save_prices


def main():
    collector = TCBBackfillCollector("tcb_backfill")
    records = collector.collect()

    inserted, skipped = save_prices(records)
    collector.logger.info(
        f"Backfill complete: {len(records)} parsed, {inserted} inserted, {skipped} skipped"
    )


if __name__ == "__main__":
    main()