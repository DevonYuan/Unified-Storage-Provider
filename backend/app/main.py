"""FastAPI application entrypoint.

PLACEHOLDER FOR PHASE 1 SCAFFOLDING.
The routers and middleware below are wired up at this stage so that tests
can mount the app, but the route handlers themselves are stubs that do not
yet implement the spec; tests are expected to fail until Phase 1
implementation lands.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.auth import router as auth_router

app = FastAPI(title="OmniDrive API")

# CORS: allow the local Vite frontend to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
