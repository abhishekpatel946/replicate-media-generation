"""
Real Replicate API client for Stable Diffusion image generation.
Uses synchronous requests to avoid async loop conflicts in Celery.
"""

import requests
from typing import Dict, Any
from app.core.config import settings


class ReplicateAPIError(Exception):
    """Custom exception for Replicate API errors."""

    pass


class RealReplicateClient:
    """
    Real Replicate API client that makes actual calls to Replicate's models.
    Uses synchronous requests to avoid async loop conflicts in Celery.
    """

    def __init__(self, api_token: str = None):
        self.api_token = api_token or settings.replicate_api_token
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }

    def create_prediction(
        self, model: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new prediction using the real Replicate API.

        Args:
            model: Model identifier (e.g., "black-forest-labs/flux-schnell")
            input_data: Input parameters including prompt

        Returns:
            Dictionary with job details including job ID and status

        Raises:
            ReplicateAPIError: If the API request fails
        """
        # Default to Flux Schnell model if not specified or invalid
        if not model or model == "stable-diffusion":
            model = (
                "black-forest-labs/flux-schnell:"
                "bf2f3f8fcd2c8bafa49d6f72e342c33c5463d78947f7a0eb8a6eb5da05c4e0c2"
            )

        url = f"{self.base_url}/predictions"
        payload = {
            "version": model.split(":")[-1] if ":" in model else model,
            "input": input_data,
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=30
            )
            if response.status_code == 201:
                return response.json()
            else:
                raise ReplicateAPIError(
                    f"API request failed with status {response.status_code}: "
                    f"{response.text}"
                )
        except requests.Timeout:
            raise ReplicateAPIError("Request timed out")
        except requests.RequestException as e:
            raise ReplicateAPIError(f"Network error: {str(e)}")

    def get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """
        Get prediction status and results from the real Replicate API.

        Args:
            prediction_id: The prediction job ID

        Returns:
            Updated prediction data with status and possibly results

        Raises:
            ReplicateAPIError: If the API request fails
        """
        url = f"{self.base_url}/predictions/{prediction_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                raise ReplicateAPIError(
                    f"API request failed with status {response.status_code}: "
                    f"{response.text}"
                )
        except requests.Timeout:
            raise ReplicateAPIError("Request timed out")
        except requests.RequestException as e:
            raise ReplicateAPIError(f"Network error: {str(e)}")


class ReplicateService:
    """
    High-level service for interacting with Replicate API.
    Provides business logic on top of the client.
    """

    def __init__(self):
        # Check if we should use real API or mock
        real_token = (
            settings.replicate_api_token
            and settings.replicate_api_token != "mock_token_for_demo"
        )
        if real_token:
            self.client = RealReplicateClient()
            self.use_real_api = True
        else:
            # Fall back to mock if no real token provided
            from .mock_replicate_client import MockReplicateClient

            self.client = MockReplicateClient()
            self.use_real_api = False

    def generate_image(
        self, prompt: str, model: str = "black-forest-labs/flux-schnell", **kwargs
    ) -> str:
        """
        Start image generation and return job ID.

        Args:
            prompt: Text prompt for image generation
            model: Model to use for generation
            **kwargs: Additional parameters for generation

        Returns:
            External job ID from Replicate API
        """
        # Prepare input data with optimal settings for high-quality images
        input_data = {
            "prompt": prompt,
            "width": kwargs.get("width", 1024),
            "height": kwargs.get("height", 1024),
            "num_outputs": 1,
            "num_inference_steps": kwargs.get("num_inference_steps", 4),
            "guidance_scale": kwargs.get("guidance_scale", 3.5),
            "seed": kwargs.get("seed"),
        }

        # Remove None values
        input_data = {k: v for k, v in input_data.items() if v is not None}

        response = self.client.create_prediction(model, input_data)
        return response["id"]

    def check_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a generation job.

        Args:
            job_id: External job ID from Replicate

        Returns:
            Job status information including results if completed
        """
        return self.client.get_prediction(job_id)

    def download_result(self, image_url: str, prompt: str = None) -> bytes:
        """
        Download generated image from URL.

        Args:
            image_url: URL of the generated image
            prompt: Original prompt used for generation

        Returns:
            Image data as bytes
        """
        try:
            response = requests.get(image_url, timeout=60)
            if response.status_code == 200:
                return response.content
            else:
                raise ReplicateAPIError(
                    f"Failed to download image: HTTP {response.status_code}"
                )
        except requests.Timeout:
            raise ReplicateAPIError("Image download timed out")
        except requests.RequestException as e:
            raise ReplicateAPIError(f"Network error downloading image: {str(e)}")


# Global service instance
replicate_service = ReplicateService()
