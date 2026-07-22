from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from ..core.config import settings

# Create the SQLAlchemy engine
# For PostgreSQL (Supabase), we use the provided DATABASE_URL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models
Base = declarative_base()

def get_db():
    """Dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
