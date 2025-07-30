#!/usr/bin/env python3
"""
Database initialization script for Fleek Media Service.
Creates the database schema and runs initial migrations.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import create_db_and_tables
from app.core.config import settings


async def init_database():
    """Initialize the database with tables."""
    try:
        print("Initializing database...")
        print(f"Database URL: {settings.database_url}")

        await create_db_and_tables()
        print("✅ Database tables created successfully!")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_database())
