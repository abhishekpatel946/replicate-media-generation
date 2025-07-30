"""
Job model for media generation tasks.
Tracks the lifecycle and metadata of media generation requests.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Column, DateTime, Field, SQLModel


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobBase(SQLModel):
    """Base job model with shared fields."""

    prompt: str = Field(description="Text prompt for media generation")
    model_name: str = Field(
        default="stable-diffusion", description="AI model to use for generation"
    )
    parameters: Optional[str] = Field(
        default=None, description="JSON string of generation parameters"
    )
    status: JobStatus = Field(
        default=JobStatus.PENDING, description="Current job status"
    )


class Job(JobBase, table=True):
    """Job database model."""

    id: UUID = Field(
        default_factory=uuid4, primary_key=True, description="Unique job identifier"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True)),
        description="Job creation timestamp",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Last update timestamp",
    )
    started_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Processing start timestamp",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Processing completion timestamp",
    )

    # Processing metadata
    retry_count: int = Field(default=0, description="Number of retry attempts")
    error_message: Optional[str] = Field(
        default=None, description="Error message if job failed"
    )

    # Result metadata
    result_url: Optional[str] = Field(
        default=None, description="URL to the generated media file"
    )
    file_path: Optional[str] = Field(
        default=None, description="Local file system path to the generated media"
    )
    file_size: Optional[int] = Field(
        default=None, description="Size of the generated file in bytes"
    )

    # External service metadata
    external_job_id: Optional[str] = Field(
        default=None, description="Job ID from external service (e.g., Replicate)"
    )


class JobCreate(JobBase):
    """Schema for creating a new job."""

    pass


class JobUpdate(SQLModel):
    """Schema for updating job fields."""

    status: Optional[JobStatus] = None
    error_message: Optional[str] = None
    result_url: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    external_job_id: Optional[str] = None
    retry_count: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobResponse(JobBase):
    """Schema for job API responses."""

    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int
    error_message: Optional[str]
    result_url: Optional[str]
    file_size: Optional[int]
