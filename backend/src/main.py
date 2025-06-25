"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import get_settings
from .logger import logger
from .routers import health

settings = get_settings()

app = FastAPI(
    title="Executive AI Backend",
    description="Backend API for Executive AI MVP",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health")

@app.get("/")
async def root():
    """Redirect root to docs."""
    return RedirectResponse(url="/docs")

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Executive AI Backend")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Executive AI Backend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )