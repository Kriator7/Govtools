#!/usr/bin/env python3
"""Import investors from CSV or Excel."""

import argparse
from pathlib import Path

from app.db import get_session_factory, init_db
from app.services.importing import InvestorImportService
from app.services.seed import seed_realtor


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    init_db()
    db = get_session_factory()()
    try:
        realtor = seed_realtor(db)
        result = InvestorImportService(db).import_path(realtor, args.path)
        db.commit()
        print(result)
        return 0 if not result["errors"] else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
