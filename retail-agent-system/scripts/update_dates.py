"""
Update all existing records to realistic dates from 2026-01-01 to today.
Run once from the retail-agent-system directory:
    python -m scripts.update_dates
"""
import sys
import os
import random
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.database import SessionLocal

START = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
END   = datetime.now(timezone.utc)


def _day_weight(weekday: int) -> float:
    # Mon=0 … Sun=6. Weekdays are busier; each day gets a random variation too.
    base = [1.2, 1.3, 1.2, 1.4, 1.5, 0.7, 0.4]
    return base[weekday] * random.uniform(0.75, 1.40)


def _build_day_pool():
    pool = []
    d = START.date()
    while d <= END.date():
        pool.append((d, _day_weight(d.weekday())))
        d += timedelta(days=1)
    return pool


def _random_business_time():
    # Weighted toward lunch peak (12-14) and evening peak (17-21)
    r = random.random()
    if r < 0.25:
        h = random.randint(9, 11)    # morning slow
    elif r < 0.55:
        h = random.randint(12, 13)   # lunch peak
    elif r < 0.72:
        h = random.randint(14, 16)   # afternoon
    elif r < 0.97:
        h = random.randint(17, 21)   # evening peak
    else:
        h = 21
    return h, random.randint(0, 59), random.randint(0, 59)


def generate_sorted_datetimes(count: int) -> list:
    pool = _build_day_pool()
    total_w = sum(w for _, w in pool)
    dates = []
    for _ in range(count):
        r = random.uniform(0, total_w)
        cum = 0.0
        chosen = pool[-1][0]
        for d, w in pool:
            cum += w
            if r <= cum:
                chosen = d
                break
        h, m, s = _random_business_time()
        dates.append(datetime(chosen.year, chosen.month, chosen.day, h, m, s, tzinfo=timezone.utc))
    dates.sort()
    return dates


def update_table(db, table: str, date_col: str, label: str):
    rows = db.execute(text(f"SELECT id FROM {table} ORDER BY id ASC")).fetchall()
    if not rows:
        print(f"  {label}: empty, skipping.")
        return
    ids   = [r[0] for r in rows]
    dates = generate_sorted_datetimes(len(ids))
    for rid, dt in zip(ids, dates):
        db.execute(
            text(f"UPDATE {table} SET {date_col} = :dt WHERE id = :id"),
            {"dt": dt, "id": rid},
        )
    db.commit()
    print(f"  {label}: {len(ids):>5} records  "
          f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")


def main():
    print(f"Date range  : {START.date()} to {END.date()}")
    print(f"Total days  : {(END.date() - START.date()).days + 1}\n")

    db = SessionLocal()
    try:
        update_table(db, "invoices",        "created_at", "Invoices       ")
        update_table(db, "sales",           "sale_date",  "Sales          ")
        update_table(db, "purchase_orders", "created_at", "Purchase Orders")
        update_table(db, "complaints",      "created_at", "Complaints     ")
        update_table(db, "notifications",   "created_at", "Notifications  ")
        update_table(db, "chat_messages",   "created_at", "Chat Messages  ")
        update_table(db, "promotions",      "created_at", "Promotions     ")

        print("\nAll records updated successfully.")
        print("Restart the backend, then verify:")
        print("  - Sales Dashboard: Last 7 / 14 / 30 days show different revenue figures")
        print("  - AI Agent: 'Show financial summary for last 30 days' = non-zero results")
        print("  - AI Agent: 'Calculate profit and loss for last 7 days' = non-zero results")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
