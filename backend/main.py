"""OmniDrive Backend - Unified Cloud Storage Pool API."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database_driver import init_db, engine
from routers import auth, storage, omnidrive


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize database on startup."""
    # Initialize database tables on startup
    init_db()
    yield
    # Cleanup on shutdown
    engine.dispose()


app = FastAPI(
    title="OmniDrive API",
    description="Unified Cloud Storage Pool - Manage Google Drive and OneDrive as a single storage pool",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration for local frontend development and packaged Electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://192.168.1.166:5173",
        "http://172.31.224.1:5173",
        "http://172.29.176.1:5173",
        # Packaged Electron loads frontend via file://, browser sends Origin: null
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(storage.router)
app.include_router(omnidrive.router)


@app.get("/")
def root():
    """Root endpoint - health check."""
    return {
        "name": "OmniDrive API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")