#!/usr/bin/env python3
"""
Comprehensive image generation test script for Fleek Media Service.
Tests the complete flow from job creation to image download with
quality verification.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
from PIL import Image


class ImageGenerationTester:
    """Comprehensive tester for the image generation flow."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.storage_path = Path("storage/media")

    async def test_complete_flow(self):
        """Test the complete image generation flow."""
        print("🚀 Starting comprehensive image generation test...")
        print(f"🔗 API Base URL: {self.base_url}")

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                # Step 1: Health check
                await self._test_health_check(client)

                # Step 2: Create high-quality image generation job
                job_id = await self._create_generation_job(client)

                # Step 3: Monitor job progress
                job_result = await self._monitor_job_progress(client, job_id)

                # Step 4: Download and verify image
                if job_result["status"] == "completed":
                    await self._download_and_verify_image(client, job_id, job_result)
                else:
                    print(
                        f"❌ Job failed: {job_result.get('error_message', 'Unknown error')}"
                    )
                    return False

                print("\n✅ Complete image generation flow test PASSED!")
                return True

            except Exception as e:
                print(f"❌ Test failed with error: {e}")
                return False

    async def _test_health_check(self, client: httpx.AsyncClient):
        """Test API health and service info."""
        print("\n🔍 Step 1: Testing API health...")

        # Health check
        response = await client.get(f"{self.base_url}/health")
        if response.status_code == 200:
            print("✅ API health check passed")
        else:
            raise Exception(f"Health check failed: {response.status_code}")

        # Service info
        try:
            response = await client.get(f"{self.base_url}/info")
            if response.status_code == 200:
                info = response.json()
                print(
                    f"✅ Service info: {info.get('name', 'Unknown')} v{info.get('version', 'Unknown')}"
                )
        except Exception:
            print("⚠️ Service info endpoint not available (this is okay)")

    async def _create_generation_job(self, client: httpx.AsyncClient) -> str:
        """Create a high-quality image generation job."""
        print("\n🔍 Step 2: Creating image generation job...")

        # High-quality prompt for testing
        job_data = {
            "prompt": "A photorealistic landscape of a serene mountain lake at sunset, with crystal clear reflections, vibrant orange and purple sky, snow-capped peaks, and a wooden dock extending into the water. Ultra-detailed, 8K quality, professional photography style.",
            "model_name": "black-forest-labs/flux-schnell",
            "parameters": json.dumps(
                {
                    "width": 1024,
                    "height": 1024,
                    "num_inference_steps": 4,
                    "guidance_scale": 3.5,
                }
            ),
        }

        print(f"📝 Prompt: {job_data['prompt'][:100]}...")
        print(f"🤖 Model: {job_data['model_name']}")

        response = await client.post(f"{self.base_url}/api/v1/generate", json=job_data)

        if response.status_code == 201:
            job = response.json()
            job_id = job["id"]
            print(f"✅ Job created successfully!")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {job['status']}")
            return job_id
        else:
            error_msg = f"Job creation failed: {response.status_code} - {response.text}"
            raise Exception(error_msg)

    async def _monitor_job_progress(
        self, client: httpx.AsyncClient, job_id: str
    ) -> dict:
        """Monitor job progress until completion or failure."""
        print(f"\n🔍 Step 3: Monitoring job progress...")

        max_attempts = 60  # 10 minutes max (10 seconds between checks)

        for attempt in range(max_attempts):
            response = await client.get(f"{self.base_url}/api/v1/status/{job_id}")

            if response.status_code == 200:
                job_status = response.json()
                status = job_status["status"]

                print(f"   Attempt {attempt + 1:2d}/60: Status = {status}")

                if status == "completed":
                    print("✅ Job completed successfully!")
                    self._print_job_details(job_status)
                    return job_status
                elif status == "failed":
                    print(
                        f"❌ Job failed: {job_status.get('error_message', 'Unknown error')}"
                    )
                    return job_status
                elif status in ["pending", "processing"]:
                    # Show progress indicators
                    if status == "processing":
                        print("   🔄 Image generation in progress...")
                    await asyncio.sleep(10)  # Wait 10 seconds before next check
                    continue
                else:
                    print(f"⚠️ Unexpected status: {status}")
                    await asyncio.sleep(10)
                    continue
            else:
                print(f"❌ Status check failed: {response.status_code}")
                raise Exception(f"Status check failed: {response.status_code}")

        raise Exception("Job timed out after 10 minutes")

    def _print_job_details(self, job_status: dict):
        """Print detailed job information."""
        print("📊 Job Details:")
        print(f"   Created: {job_status.get('created_at', 'Unknown')}")
        print(f"   Started: {job_status.get('started_at', 'Unknown')}")
        print(f"   Completed: {job_status.get('completed_at', 'Unknown')}")
        print(f"   File Size: {job_status.get('file_size', 0):,} bytes")
        print(f"   Result URL: {job_status.get('result_url', 'None')}")

    async def _download_and_verify_image(
        self, client: httpx.AsyncClient, job_id: str, job_result: dict
    ):
        """Download image and verify quality, size, and accuracy."""
        print(f"\n🔍 Step 4: Downloading and verifying image...")

        # Download via API endpoint
        response = await client.get(f"{self.base_url}/api/v1/download/{job_id}")

        if response.status_code == 200:
            print("✅ Image download successful!")

            # Save to storage directory
            image_data = response.content
            image_path = self.storage_path / f"generated_{job_id}.png"

            # Ensure storage directory exists
            self.storage_path.mkdir(parents=True, exist_ok=True)

            with open(image_path, "wb") as f:
                f.write(image_data)

            print(f"💾 Image saved to: {image_path}")

            # Verify the image
            await self._verify_image_quality(image_path, job_result)

        else:
            raise Exception(
                f"Image download failed: {response.status_code} - {response.text}"
            )

    async def _verify_image_quality(self, image_path: Path, job_result: dict):
        """Verify image quality, size, and technical specifications."""
        print("\n🔍 Image Quality Verification:")

        try:
            # Open and analyze the image
            with Image.open(image_path) as img:
                # Basic image properties
                width, height = img.size
                format_info = img.format
                mode = img.mode

                print(f"📐 Image Dimensions: {width} x {height} pixels")
                print(f"🎨 Format: {format_info}")
                print(f"🌈 Color Mode: {mode}")

                # File size verification
                file_size = image_path.stat().st_size
                expected_size = job_result.get("file_size", 0)

                print(f"📦 File Size: {file_size:,} bytes")
                if expected_size:
                    print(f"📦 Expected Size: {expected_size:,} bytes")
                    size_match = (
                        abs(file_size - expected_size) < 1000
                    )  # Allow 1KB difference
                    print(f"✅ Size Match: {'Yes' if size_match else 'No'}")

                # Quality assessment
                self._assess_image_quality(img, width, height)

                # Detailed technical specs
                print("\n📋 Technical Specifications:")
                print(f"   Color Channels: {len(img.getbands())}")
                print(f"   Has Transparency: {'Yes' if 'A' in img.mode else 'No'}")
                print(
                    f"   Compression: {'PNG' if format_info == 'PNG' else format_info}"
                )

                # Save verification report
                self._save_verification_report(image_path, img, job_result)

        except Exception as e:
            print(f"❌ Image verification failed: {e}")
            raise

    def _assess_image_quality(self, img: Image, width: int, height: int):
        """Assess image quality metrics."""
        print("\n🎯 Quality Assessment:")

        # Resolution check
        total_pixels = width * height
        print(f"   Total Pixels: {total_pixels:,}")

        if total_pixels >= 1000000:  # 1MP+
            print("   ✅ High Resolution (1MP+)")
        elif total_pixels >= 500000:  # 0.5MP+
            print("   ✅ Good Resolution (0.5MP+)")
        else:
            print("   ⚠️ Lower Resolution (<0.5MP)")

        # Aspect ratio
        aspect_ratio = width / height
        print(f"   Aspect Ratio: {aspect_ratio:.2f}:1")

        if abs(aspect_ratio - 1.0) < 0.1:
            print("   ✅ Square format (good for social media)")
        elif 1.3 <= aspect_ratio <= 1.8:
            print("   ✅ Standard landscape format")
        else:
            print(f"   ℹ️ Custom aspect ratio")

        # Color analysis (basic)
        if img.mode in ["RGB", "RGBA"]:
            # Convert to RGB for analysis
            rgb_img = img.convert("RGB")
            colors = rgb_img.getcolors(maxcolors=1000000)
            if colors:
                unique_colors = len(colors)
                print(f"   Color Diversity: {unique_colors:,} unique colors")
                if unique_colors > 10000:
                    print("   ✅ High color diversity (photorealistic)")
                elif unique_colors > 1000:
                    print("   ✅ Good color diversity")
                else:
                    print("   ⚠️ Limited color palette")

    def _save_verification_report(self, image_path: Path, img: Image, job_result: dict):
        """Save a detailed verification report."""
        report_path = image_path.with_suffix(".verification.json")

        # Calculate some basic statistics
        width, height = img.size
        file_size = image_path.stat().st_size

        report = {
            "image_path": str(image_path),
            "verification_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dimensions": {"width": width, "height": height},
            "format": img.format,
            "mode": img.mode,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "total_pixels": width * height,
            "aspect_ratio": round(width / height, 2),
            "job_result": job_result,
            "quality_score": self._calculate_quality_score(img, file_size),
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📄 Verification report saved: {report_path}")
        print(f"🏆 Overall Quality Score: {report['quality_score']}/100")

    def _calculate_quality_score(self, img: Image, file_size: int) -> int:
        """Calculate a simple quality score (0-100)."""
        score = 0
        width, height = img.size
        total_pixels = width * height

        # Resolution score (0-40 points)
        if total_pixels >= 1000000:
            score += 40
        elif total_pixels >= 500000:
            score += 30
        elif total_pixels >= 100000:
            score += 20
        else:
            score += 10

        # File size appropriateness (0-20 points)
        size_mb = file_size / (1024 * 1024)
        if 0.5 <= size_mb <= 10:  # Reasonable size
            score += 20
        elif size_mb <= 20:
            score += 15
        else:
            score += 10

        # Format score (0-20 points)
        if img.format == "PNG":
            score += 20
        elif img.format in ["JPEG", "JPG"]:
            score += 15
        else:
            score += 10

        # Color mode score (0-20 points)
        if img.mode == "RGB":
            score += 20
        elif img.mode == "RGBA":
            score += 15
        else:
            score += 10

        return min(score, 100)


async def main():
    """Main test function."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"

    print("🎨 Fleek Media Service - Image Generation Test")
    print("=" * 50)

    tester = ImageGenerationTester(base_url)
    success = await tester.test_complete_flow()

    if success:
        print("\n🎉 All tests PASSED! Image generation flow is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Tests FAILED! Please check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    print(
        "Make sure the API server is running and you have added your REPLICATE_API_TOKEN to config.env"
    )
    asyncio.run(main())
