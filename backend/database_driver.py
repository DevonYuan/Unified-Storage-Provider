"""Database driver for OmniDrive - SQLite with SQLAlchemy."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import sys

# App configuration
APP_NAME = "OmniDrive"

# Get the OS-appropriate app data directory
if os.name == 'nt':  # Windows
    # On Windows, use AppData/Local/OmniDrive directly
    DATA_DIR = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))) / APP_NAME
else:
    # On Unix-like systems, use platformdirs for proper XDG compliance
    from platformdirs import user_data_dir
    DATA_DIR = Path(user_data_dir(APP_NAME))

DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database path
DB_PATH = DATA_DIR / "omnidrive.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with proper SQLite settings
engine = create_engine(
    DATABASE_URL,
    
    connect_args={"check_same_thread": False},  # Required for SQLite with FastAPI
    echo=False,  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables. Call this on app startup."""
    # Import all models here so they are registered with Base
    from models import ConnectedAccount  # noqa: F401
    Base.metadata.create_all(bind=engine)