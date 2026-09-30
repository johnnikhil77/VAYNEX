"""Seed the Vaynex demo dataset (Hyderabad) and demo accounts.

Usage:
    python scripts/seed_demo.py            # uses DATABASE_URL / .env
    python scripts/seed_demo.py --no-users # topology only

Idempotent: safe to run repeatedly. Refuses to create demo accounts when
ENVIRONMENT=production unless --force is given.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.core.config import get_settings  # noqa: E402
from apps.api.services.demo_data import demo_users, seed_demo_data  # noqa: E402
from packages.database.session import create_engine, create_session_factory, session_scope  # noqa: E402


async def main(with_users: bool, force: bool) -> int:
    settings = get_settings()
    if with_users and settings.ENVIRONMENT == "production" and not force:
        print("Refusing to create demo accounts in production (use --force to override).", file=sys.stderr)
        return 2
    engine = create_engine(settings.DATABASE_URL, null_pool=True)
    try:
        async with session_scope(create_session_factory(engine)) as session:
            report = await seed_demo_data(session, with_users=with_users)
            await session.commit()
    finally:
        await engine.dispose()

    print("Vaynex demo data seeded:")
    for key, value in report.as_dict().items():
        print(f"  {key:<15} +{value}")
    if with_users:
        print("\nDemo accounts (override passwords with DEMO_*_PASSWORD env vars):")
        for user in demo_users():
            print(f"  {user['role'].value:<9} {user['email']:<24} {user['password']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Vaynex demo data")
    parser.add_argument("--no-users", action="store_true", help="Do not create demo user accounts")
    parser.add_argument("--force", action="store_true", help="Allow demo accounts in production")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(with_users=not args.no_users, force=args.force)))
