"""
FastAPI endpoints for media generation service.
Handles job creation and status checking.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.models.job import Job, JobCreate, JobResponse, JobStatus
from app.services.storage import storage_service, StorageError
from app.tasks.media_tasks import process_media_generation

router = APIRouter(prefix="/api/v1", tags=["media"])


@router.post(
    "/generate",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new media generation job",
    description="Submit a prompt for async media generation",
)
async def create_generation_job(
    job_request: JobCreate, session: AsyncSession = Depends(get_session)
) -> JobResponse:
    """
    Create a new media generation job.

    The job will be processed asynchronously by Celery workers.
    Use the returned job ID to check status and retrieve results.

    Args:
        job_request: Job creation parameters including prompt
        session: Database session

    Returns:
        Created job details including unique ID

    Raises:
        HTTPException: If job creation fails
    """
    try:
        # Create job in database
        job = Job.model_validate(job_request.model_dump())
        session.add(job)
        await session.commit()
        await session.refresh(job)

        # Queue background task
        process_media_generation.delay(str(job.id))

        return JobResponse.model_validate(job.model_dump())

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}",
        )


@router.get(
    "/status/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    description="Check the status and results of a generation job",
)
async def get_job_status(
    job_id: UUID, session: AsyncSession = Depends(get_session)
) -> JobResponse:
    """
    Get the current status of a media generation job.

    Args:
        job_id: Unique job identifier
        session: Database session

    Returns:
        Job details including current status and results if available

    Raises:
        HTTPException: If job not found
    """
    try:
        # Get job from database
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Job {job_id} not found"
            )

        return JobResponse.model_validate(job.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}",
        )


@router.get(
    "/download/{job_id}",
    summary="Download generated media",
    description="Download the generated media file for a completed job",
    response_class=FileResponse,
)
async def download_media_file(
    job_id: UUID, session: AsyncSession = Depends(get_session)
) -> FileResponse:
    """
    Download the generated media file.

    Args:
        job_id: Unique job identifier
        session: Database session

    Returns:
        File response with generated media

    Raises:
        HTTPException: If job not found, not completed, or file missing
    """
    try:
        # Get job from database
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Job {job_id} not found"
            )

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} is not completed. Status: {job.status}",
            )

        if not job.file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No file available for job {job_id}",
            )

        # Verify file exists
        try:
            await storage_service.get_file(job_id)
            # Save to temporary location for FileResponse
            temp_path = storage_service.get_file_path(job_id)

            return FileResponse(
                path=temp_path,
                filename=f"generated_{job_id}.png",
                media_type="image/png",
            )

        except StorageError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found for job {job_id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}",
        )


@router.get(
    "/jobs",
    response_model=List[JobResponse],
    summary="List all jobs",
    description="List all media generation jobs with optional filtering",
)
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(
        None, description="Filter jobs by status"
    ),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of jobs to return"
    ),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    session: AsyncSession = Depends(get_session),
) -> List[JobResponse]:
    """
    List all media generation jobs.

    Args:
        status_filter: Optional status filter
        limit: Maximum number of jobs to return (1-100)
        offset: Number of jobs to skip for pagination
        session: Database session

    Returns:
        List of jobs matching the criteria

    Raises:
        HTTPException: If query fails
    """
    try:
        # Build query
        query = select(Job).order_by(Job.created_at.desc())
        
        # Apply status filter if provided
        if status_filter:
            query = query.where(Job.status == status_filter)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await session.execute(query)
        jobs = result.scalars().all()

        return [JobResponse.model_validate(job.model_dump()) for job in jobs]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}",
        )


@router.get(
    "/jobs/{job_id}/metadata",
    summary="Get job metadata",
    description="Get the generation metadata for a specific job",
)
async def get_job_metadata(
    job_id: UUID, session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get the generation metadata for a job.

    Args:
        job_id: Unique job identifier
        session: Database session

    Returns:
        Generation metadata including parameters used

    Raises:
        HTTPException: If job not found or metadata not available
    """
    try:
        # Check if job exists
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Job {job_id} not found"
            )

        # Get metadata from storage
        try:
            metadata = await storage_service.get_metadata(job_id)
            return metadata
        except StorageError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata not found for job {job_id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job metadata: {str(e)}",
        )


@router.delete(
    "/jobs/{job_id}",
    summary="Cancel job",
    description="Cancel a pending or processing job",
)
async def cancel_job(
    job_id: UUID, session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Cancel a media generation job.

    Only pending or processing jobs can be cancelled.

    Args:
        job_id: Unique job identifier
        session: Database session

    Returns:
        Cancellation status

    Raises:
        HTTPException: If job not found or cannot be cancelled
    """
    try:
        # Get job from database
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Job {job_id} not found"
            )

        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {job.status}",
            )

        # Update job status
        job.status = JobStatus.CANCELLED
        await session.commit()

        return {"message": f"Job {job_id} cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}",
        )
