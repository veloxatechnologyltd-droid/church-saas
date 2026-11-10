"""Permanently delete churches whose closure retention period has ended.

Run once a day from a platform cron job (Render cron, or any scheduler). Safe to repeat:
only churches that are closed AND past ``purge_after`` are touched. Prints a summary with
no personal data.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal
from app.services.closure import purge_due


def main() -> None:
    db = SessionLocal()
    try:
        results = purge_due(db)
        print({"purged": len(results), "results": results})
    finally:
        db.close()


if __name__ == "__main__":
    main()
