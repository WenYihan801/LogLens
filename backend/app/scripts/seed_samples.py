"""Load the synthetic sample datasets (FR-32).

    python -m app.scripts.seed_samples            # load samples not yet present
    python -m app.scripts.seed_samples --reset    # delete ALL datasets first

Used to pre-compute results for the public read-only demo: run it once against
the demo database with write access, then start the API with DEMO_READ_ONLY=true.
"""

import argparse
import sys

from sqlalchemy import delete, select

from app.database.connection import SessionLocal
from app.database.models import Dataset
from app.services import dataset_service
from app.services.detection.engine import sync_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="delete all datasets before seeding")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        sync_rules(db)
        if args.reset:
            db.execute(delete(Dataset))
            db.commit()
            print("Deleted all datasets.")
        existing = set(db.scalars(select(Dataset.name)))
        for info in dataset_service.list_samples():
            if info.name in existing:
                print(f"skip  {info.name} (already loaded)")
                continue
            res = dataset_service.import_sample(db, info.key)
            print(
                f"load  {info.name}: {res['parsed_lines']} parsed, {res['failed_lines']} failed, "
                f"{res['alerts_generated']} alerts"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
