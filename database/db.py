def save_prices(records):
    conn = get_connection()
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    optional_fields = [
        "item_en",
        "category",
        "source_url",
        "collector_script",
        "notes",
    ]

    query = """
    INSERT INTO market_prices (
        price_date, item_bn, item_en, category,
        market_name, source_name, source_type,
        price_type, price_min, price_max,
        unit, source_url, collector_script, notes
    )
    VALUES (
        %(price_date)s, %(item_bn)s, %(item_en)s, %(category)s,
        %(market_name)s, %(source_name)s, %(source_type)s,
        %(price_type)s, %(price_min)s, %(price_max)s,
        %(unit)s, %(source_url)s, %(collector_script)s, %(notes)s
    )
    ON CONFLICT (
        price_date, item_bn, unit,
        market_name, source_name, price_type
    ) DO NOTHING;
    """

    try:
        for record in records:
            for field in optional_fields:
                record.setdefault(field, None)

            try:
                cur.execute(query, record)

                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1

            except Exception as e:
                print(f"Skipping record: {e}")
                conn.rollback()
                continue

        conn.commit()

    finally:
        cur.close()
        conn.close()

    return inserted, skipped