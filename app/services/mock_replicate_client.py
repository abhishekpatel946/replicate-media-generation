"""
Mock Replicate API client for demo/fallback purposes.
"""

import asyncio
import hashlib
import io
import random
from typing import Dict, Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont
from app.core.config import settings


class ReplicateAPIError(Exception):
    """Custom exception for Replicate API errors."""

    pass


class MockReplicateClient:
    """
    Mock Replicate API client that simulates real API behavior.
    """

    def __init__(self, api_token: str = None):
        self.api_token = api_token or settings.replicate_api_token
        self.base_url = "https://api.replicate.com/v1"

    async def create_prediction(
        self, model: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a mock prediction."""
        # Simulate API processing delay
        delay = random.uniform(
            settings.replicate_mock_delay_min, settings.replicate_mock_delay_max
        )
        await asyncio.sleep(delay)

        # Simulate random failures
        if random.random() < settings.replicate_mock_failure_rate:
            raise ReplicateAPIError(f"Simulated API failure for model {model}")

        # Generate mock job ID
        job_id = str(uuid4())

        # Return realistic response structure
        return {
            "id": job_id,
            "status": "processing",
            "model": model,
            "input": input_data,
            "created_at": "2024-01-01T00:00:00.000000Z",
            "started_at": None,
            "completed_at": None,
            "output": None,
            "error": None,
            "logs": "",
            "metrics": {},
        }

    async def get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Get mock prediction status."""
        # Simulate API call delay
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # Simulate random failures
        if random.random() < settings.replicate_mock_failure_rate * 0.5:
            raise ReplicateAPIError(f"Failed to fetch prediction {prediction_id}")

        # Simulate job completion (80% chance of success)
        is_completed = random.random() < 0.8
        is_failed = not is_completed and random.random() < 0.3

        if is_completed:
            # Generate mock image URL
            mock_image_url = (
                f"https://replicate.delivery/pbxt/" f"mock-image-{prediction_id}.png"
            )
            return {
                "id": prediction_id,
                "status": "succeeded",
                "completed_at": "2024-01-01T00:01:00.000000Z",
                "output": [mock_image_url],
                "error": None,
                "logs": "Mock generation completed successfully",
                "metrics": {"predict_time": random.uniform(5.0, 15.0)},
            }
        elif is_failed:
            return {
                "id": prediction_id,
                "status": "failed",
                "completed_at": "2024-01-01T00:01:00.000000Z",
                "output": None,
                "error": "Mock generation failed - insufficient GPU memory",
                "logs": "Mock error simulation",
                "metrics": {},
            }
        else:
            # Still processing
            return {
                "id": prediction_id,
                "status": "processing",
                "completed_at": None,
                "output": None,
                "error": None,
                "logs": "Mock generation in progress...",
                "metrics": {},
            }

    def _generate_mock_image(
        self, prompt: str, width: int = 512, height: int = 512
    ) -> bytes:
        """Generate a simple mock image."""
        # Create a simple colored image
        color = (100, 150, 200)  # Simple blue
        image = Image.new("RGB", (width, height), color)

        # Convert to PNG bytes
        img_byte_array = io.BytesIO()
        image.save(img_byte_array, format="PNG")
        return img_byte_array.getvalue()

    async def download_result(self, image_url: str, prompt: str = None) -> bytes:
        """Download mock result."""
        # Simulate download delay
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # Generate a simple mock image
        return self._generate_mock_image(prompt or "Generated image")
