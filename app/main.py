"""
Main FastAPI application for Fleek Media Service.
Handles application lifecycle and router registration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.media import router as media_router
from app.core.config import settings
from app.core.database import create_db_and_tables


# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Fleek Media Service...")

    try:
        # Create database tables
        await create_db_and_tables()
        logger.info("Database tables created successfully")

        # Create storage directory
        from pathlib import Path

        storage_path = Path(settings.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage directory ensured: {storage_path}")

        logger.info("Application startup completed")
        yield

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    # Shutdown
    logger.info("Shutting down Fleek Media Service...")


# Create FastAPI application
app = FastAPI(
    title="Fleek Media Service",
    description="Asynchronous media generation microservice using Replicate API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(media_router)

# Mount static files for media serving
try:
    from pathlib import Path

    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)

    app.mount("/media", StaticFiles(directory=str(storage_path)), name="media")
except Exception as e:
    logger.warning(f"Could not mount media files: {e}")


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Fleek Media Service",
        "version": "1.0.0",
        "description": "Asynchronous media generation microservice",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint for load balancers."""
    return {"status": "healthy", "service": "fleek-media-service", "version": "1.0.0"}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service dependencies."""
    import redis
    from app.core.database import engine
    
    health_status = {
        "service": "fleek-media-service",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "checks": {}
    }
    
    # Check database connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        health_status["checks"]["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Redis connectivity
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        health_status["checks"]["redis"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check storage directory
    try:
        from pathlib import Path
        storage_path = Path(settings.storage_path)
        if storage_path.exists() and storage_path.is_dir():
            health_status["checks"]["storage"] = {"status": "healthy", "message": "Directory accessible"}
        else:
            health_status["checks"]["storage"] = {"status": "unhealthy", "message": "Directory not accessible"}
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["storage"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "unhealthy"
    
    return health_status


@app.get("/metrics")
async def get_metrics():
    """Basic metrics endpoint for monitoring."""
    from sqlmodel import select, func
    from app.core.database import async_session
    from app.models.job import Job
    
    async with async_session() as session:
        try:
            # Get job counts by status
            result = await session.execute(
                select(Job.status, func.count(Job.id))
                .group_by(Job.status)
            )
            status_counts = {status: count for status, count in result.all()}
            
            # Get total job count
            total_result = await session.execute(select(func.count(Job.id)))
            total_jobs = total_result.scalar() or 0
            
            return {
                "service": "fleek-media-service",
                "metrics": {
                    "jobs_total": total_jobs,
                    "jobs_by_status": status_counts,
                    "storage_path": settings.storage_path,
                    "api_debug": settings.api_debug,
                }
            }
        except Exception as e:
            return {
                "service": "fleek-media-service",
                "error": f"Failed to collect metrics: {str(e)}"
            }


@app.get("/info")
async def service_info():
    """Service information and configuration."""
    return {
        "service": "Fleek Media Service",
        "version": "1.0.0",
        "description": "Enterprise-grade asynchronous media generation microservice",
        "environment": {
            "debug": settings.api_debug,
            "storage_path": settings.storage_path,
            "max_retry_attempts": settings.max_retry_attempts,
            "log_level": settings.log_level,
        },
        "endpoints": {
            "generate": "/api/v1/generate",
            "status": "/api/v1/status/{job_id}",
            "download": "/api/v1/download/{job_id}",
            "jobs": "/api/v1/jobs",
            "metadata": "/api/v1/jobs/{job_id}/metadata",
            "cancel": "/api/v1/jobs/{job_id}",
        },
        "monitoring": {
            "health": "/health",
            "detailed_health": "/health/detailed", 
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
    )
