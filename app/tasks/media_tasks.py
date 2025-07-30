"""
Celery tasks for media generation processing.
Handles the sync workflow from job creation to completion.
"""

import time
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.models.job import Job, JobStatus
from app.services.replicate_client import replicate_service, ReplicateAPIError
from app.services.storage import storage_service, StorageError
from app.tasks.celery_app import celery_app


def get_job_by_id(session: Session, job_id: UUID) -> Job:
    """Get job from database by ID."""
    job = session.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")
    return job


def update_job(session: Session, job_id: UUID, **updates):
    """Update job in database."""
    job = session.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")

    # Apply updates
    for field, value in updates.items():
        setattr(job, field, value)

    job.updated_at = datetime.utcnow()
    session.commit()
    return job


@celery_app.task(
    bind=True,
    autoretry_for=(ReplicateAPIError, StorageError, Exception),
    retry_kwargs={
        "max_retries": settings.max_retry_attempts,
        "countdown": 60,
    },
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def process_media_generation(self, job_id: str):
    """
    Main task for processing media generation jobs.

    This task:
    1. Starts the generation via Replicate API
    2. Polls for completion
    3. Downloads and stores the result
    4. Updates job status
    """

    # Create sync database session
    sync_engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=sync_engine)

    with SessionLocal() as session:
        try:
            job_uuid = UUID(job_id)

            # Get job details
            job = get_job_by_id(session, job_uuid)

            # Update status to processing
            update_job(
                session,
                job_uuid,
                status=JobStatus.PROCESSING,
                started_at=datetime.utcnow(),
                retry_count=self.request.retries,
            )

            # Step 1: Start generation if not already started
            if not job.external_job_id:
                try:
                    # Parse generation parameters
                    params = {}
                    if job.parameters:
                        try:
                            params = json.loads(job.parameters)
                        except json.JSONDecodeError:
                            params = {}

                    external_job_id = replicate_service.generate_image(
                        prompt=job.prompt, model=job.model_name, **params
                    )

                    update_job(
                        session, job_uuid, external_job_id=external_job_id
                    )
                    job.external_job_id = external_job_id

                    # Save generation metadata
                    metadata = {
                        "prompt": job.prompt,
                        "model_name": job.model_name,
                        "external_job_id": external_job_id,
                        "created_at": job.created_at.isoformat(),
                        **params
                    }
                    
                    # Save metadata synchronously (Celery tasks aren't async)
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            storage_service.save_metadata(job_uuid, metadata)
                        )
                    finally:
                        loop.close()

                except ReplicateAPIError as e:
                    update_job(
                        session,
                        job_uuid,
                        status=JobStatus.FAILED,
                        error_message=f"Failed to start generation: {str(e)}",
                        completed_at=datetime.utcnow(),
                    )
                    raise

            # Step 2: Poll for completion
            max_attempts = 30  # 5 minutes max
            for attempt in range(max_attempts):
                try:
                    result = replicate_service.check_job_status(
                        job.external_job_id
                    )

                    if result["status"] == "succeeded":
                        # Step 3: Download and store result
                        if result.get("output") and len(result["output"]) > 0:
                            image_url = result["output"][0]
                            image_data = replicate_service.download_result(
                                image_url, job.prompt
                            )

                            # Store file
                            file_path, file_url = storage_service.save_file(
                                job_id=job_uuid, file_data=image_data, extension="png"
                            )

                            # Update job with success
                            update_job(
                                session,
                                job_uuid,
                                status=JobStatus.COMPLETED,
                                result_url=file_url,
                                file_path=file_path,
                                file_size=len(image_data),
                                completed_at=datetime.utcnow(),
                            )

                            return {
                                "status": "completed",
                                "result_url": file_url,
                                "file_size": len(image_data),
                            }

                    elif result["status"] == "failed":
                        # External job failed
                        error_msg = result.get(
                            "error", "Unknown error from Replicate"
                        )

                        update_job(
                            session,
                            job_uuid,
                            status=JobStatus.FAILED,
                            error_message=f"Generation failed: {error_msg}",
                            completed_at=datetime.utcnow(),
                        )

                        return {"status": "failed", "error": error_msg}

                    else:
                        # Still processing - wait and retry
                        time.sleep(10)  # Wait 10 seconds before next check
                        continue

                except ReplicateAPIError as e:
                    update_job(
                        session,
                        job_uuid,
                        status=JobStatus.FAILED,
                        error_message=f"API error: {str(e)}",
                        completed_at=datetime.utcnow(),
                    )
                    raise

            # If we get here, job timed out
            update_job(
                session,
                job_uuid,
                status=JobStatus.FAILED,
                error_message="Job timed out after 5 minutes",
                completed_at=datetime.utcnow(),
            )
            return {"status": "failed", "error": "Job timed out"}

        except Exception as e:
            # Handle unexpected errors
            try:
                update_job(
                    session,
                    job_uuid,
                    status=JobStatus.FAILED,
                    error_message=f"Unexpected error: {str(e)}",
                    completed_at=datetime.utcnow(),
                )
            except Exception:
                pass  # Don't fail on update failure

            raise


@celery_app.task
def cleanup_old_files(days_old: int = 7):
    """
    Cleanup task to remove old generated files.

    Args:
        days_old: Number of days after which files should be deleted
    """
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    # Create sync database session
    sync_engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=sync_engine)

    with SessionLocal() as session:
        # Find completed jobs older than cutoff
        old_jobs = (
            session.query(Job)
            .filter(
                Job.status == JobStatus.COMPLETED,
                Job.completed_at < cutoff_date,
                Job.file_path.isnot(None),
            )
            .all()
        )

        deleted_count = 0
        for job in old_jobs:
            try:
                # Delete file from storage (this is already sync)
                if storage_service.delete_file(job.id):
                    deleted_count += 1

                    # Clear file references from job
                    update_job(session, job.id, file_path=None, result_url=None)

            except StorageError:
                continue  # Skip files that can't be deleted

        return {"deleted_files": deleted_count}
