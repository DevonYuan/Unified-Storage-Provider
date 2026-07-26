"""Auth routes: session creation and current-user lookup.

PLACEHOLDER FOR PHASE 1 SCAFFOLDING.
The handlers below are intentionally stubbed (return 501) so that tests
written in the next to-do fail meaningfully. Once implementation lands,
the same routes will return the real SessionResponse/UserResponse shapes.
"""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/session")
async def create_session() -> dict[str, str]:
    """Stub: real implementation creates/returns the single user + JWT."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="POST /auth/session not implemented",
    )


@router.get("/me")
async def get_me() -> dict[str, str]:
    """Stub: real implementation returns the authenticated user's row."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="GET /auth/me not implemented",
    )
