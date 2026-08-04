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
    from models import ConnectedAccount, UploadRouting, RepairLog  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Seed the upload routing row if it doesn't exist
    db = SessionLocal()
    try:
        from models import UploadRouting, ProviderType
        existing = db.query(UploadRouting).first()
        if not existing:
            db.add(UploadRouting(id=1, next_provider=ProviderType.GOOGLE_DRIVE))
            db.commit()

        # Clean up duplicate ConnectedAccount rows (same provider + keyring_key).
        # Keeps the most recently updated one, deletes older stale duplicates.
        # Also normalises any leftover old-format keyring_keys first.
        from sqlalchemy import func

        # One-time migration: fix old keyring_key formats
        # Old format: omnidrive:google:{id}  →  New format: google_drive:{id}
        old_format_google = (
            db.query(ConnectedAccount)
            .filter(
                ConnectedAccount.provider == ProviderType.GOOGLE_DRIVE,
                ConnectedAccount.keyring_key.startswith("omnidrive:google:"),
            )
            .all()
        )
        for acc in old_format_google:
            user_id = acc.keyring_key.split("omnidrive:google:")[1]
            new_key = f"google_drive:{user_id}"
            # Check if an account with the new key already exists
            conflict = db.query(ConnectedAccount).filter(
                ConnectedAccount.keyring_key == new_key,
                ConnectedAccount.id != acc.id,
            ).first()
            if conflict:
                # Keep the newer one, delete the older
                if acc.updated_at > conflict.updated_at:
                    db.delete(conflict)
                    acc.keyring_key = new_key
                else:
                    db.delete(acc)
            else:
                acc.keyring_key = new_key
        if old_format_google:
            db.commit()

        duplicates = (
            db.query(
                ConnectedAccount.provider,
                ConnectedAccount.keyring_key,
                func.count(ConnectedAccount.id).label("cnt"),
            )
            .group_by(ConnectedAccount.provider, ConnectedAccount.keyring_key)
            .having(func.count(ConnectedAccount.id) > 1)
            .all()
        )
        for provider, keyring_key, _ in duplicates:
            rows = (
                db.query(ConnectedAccount)
                .filter(
                    ConnectedAccount.provider == provider,
                    ConnectedAccount.keyring_key == keyring_key,
                )
                .order_by(ConnectedAccount.updated_at.desc())
                .all()
            )
            # Keep the first (most recent), delete the rest
            for row in rows[1:]:
                db.delete(row)
        if duplicates:
            db.commit()
    finally:
        db.close()