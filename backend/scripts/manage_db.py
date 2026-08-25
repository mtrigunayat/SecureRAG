"""
Database management CLI

Provides commands for database migrations and seeding.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.logging import setup_logging, get_logger
from app.db.seed import seed_database

setup_logging()
logger = get_logger(__name__)


def migrate():
    """Run database migrations."""
    import subprocess
    logger.info("Running database migrations...")
    result = subprocess.run(["alembic", "upgrade", "head"], cwd=Path(__file__).parent.parent)
    if result.returncode == 0:
        logger.info("Migrations completed successfully")
    else:
        logger.error("Migrations failed")
        sys.exit(1)


def seed():
    """Seed the database with initial data."""
    logger.info("Seeding database...")
    try:
        seed_database()
        logger.info("Database seeded successfully")
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        sys.exit(1)


def reset():
    """Reset database (downgrade and upgrade)."""
    import subprocess
    logger.info("Resetting database...")
    
    # Downgrade
    logger.info("Downgrading to base...")
    result = subprocess.run(["alembic", "downgrade", "base"], cwd=Path(__file__).parent.parent)
    if result.returncode != 0:
        logger.error("Downgrade failed")
        sys.exit(1)
    
    # Upgrade
    logger.info("Upgrading to head...")
    result = subprocess.run(["alembic", "upgrade", "head"], cwd=Path(__file__).parent.parent)
    if result.returncode != 0:
        logger.error("Upgrade failed")
        sys.exit(1)
    
    logger.info("Database reset complete")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Database management commands")
    parser.add_argument(
        "command",
        choices=["migrate", "seed", "reset"],
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "migrate":
        migrate()
    elif args.command == "seed":
        seed()
    elif args.command == "reset":
        reset()


if __name__ == "__main__":
    main()
