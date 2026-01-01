"""
Script to initialize database tables.
Run this directly to create tables if they don't exist.
"""
import sys
import os
from pathlib import Path

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR.parent / ".env")

from services import db
from utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Initializing database...")
    try:
        # We need to drop tables first because we renamed columns
        # This will wipe data, but it's refined dev env
        logger.info("Dropping existing tables...")
        engine = db.get_engine()
        db.Base.metadata.drop_all(bind=engine)
        
        logger.info("Creating new tables...")
        db.init_db()
        logger.info("Database initialization completed successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)
