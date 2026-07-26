"""Async SQLAlchemy engine and session factory.

PLACEHOLDER FOR PHASE 1 SCAFFOLDING.
The real engine/session wiring and Base model definition land in the
implementation step. Importing this module should not error so tests can
load the FastAPI app.
"""

from app.config import settings

# These names are placeholders so `from app.database import engine` etc.
# does not raise during the scaffolding/tests-first phase. They will be
# replaced with real `create_async_engine(...)` and `async_sessionmaker(...)`
# objects during implementation.
engine = None
async_session = None
