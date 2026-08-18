"""Local CLI for seed, ingest, match, and the mock demonstration."""

import argparse
from app.db import get_session_factory, init_db
from app.services.demo import run_demo
from app.services.matching.runner import OpportunityMatcher
from app.services.mls.ingest import ListingIngestService
from app.services.providers import get_mls_provider
from app.services.seed import seed_pirates_ig, seed_realtor
from app.services.telegram.realtor_agent import RealtorTelegramService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Realtor acquisition agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    sub.add_parser("demo")
    sub.add_parser("ingest")
    sub.add_parser("match")
    args = parser.parse_args(argv)

    init_db()
    db = get_session_factory()()
    try:
        if args.command == "seed":
            realtor = seed_realtor(db)
            investor = seed_pirates_ig(db, realtor)
            db.commit()
            print(f"Seeded realtor {realtor.public_id} and investor {investor.public_id}")
            return 0
        if args.command == "demo":
            result = run_demo(db)
            db.commit()
            print(result)
            return 0
        realtor = seed_realtor(db)
        seed_pirates_ig(db, realtor)
        if args.command == "ingest":
            result = ListingIngestService(db, get_mls_provider()).sync(realtor)
            db.commit()
            print(result)
            return 0
        if args.command == "match":
            created = OpportunityMatcher(db).match_all(realtor)
            telegram = RealtorTelegramService(db)
            for opportunity in created:
                telegram.alert_opportunity(realtor, opportunity)
            db.commit()
            print({"created": [item.public_id for item in created]})
            return 0
    finally:
        db.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
