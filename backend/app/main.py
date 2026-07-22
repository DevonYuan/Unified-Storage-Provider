from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1 import auth

app = FastAPI(title="OmniDrive API")

# CORS configuration to allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])

@app.get("/")
def read_root():
    return {"message": "Welcome to OmniDrive API. Please use /docs for API documentation."}
