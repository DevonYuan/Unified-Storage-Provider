"""Authentication dependency.

PLACEHOLDER FOR PHASE 1 SCAFFOLDING.
The real `get_current_user` dependency decodes the bearer token, looks up
the user row, and returns it. Until implementation lands, raising 501 keeps
the route declared so tests can import/mount the app while failing the
acceptance criteria.
"""

from fastapi import HTTPException, status


async def get_current_user():  # noqa: D401 - stub signature
    """Stub auth dependency. Real implementation arrives in Phase 1."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="auth dependency not implemented",
    )
