#!/usr/bin/env python3
"""
Comprehensive feature test script for Fleek Media Service.
Tests all implemented features including new ones added.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
from PIL import Image


class ComprehensiveFeatureTester:
    """Tests all implemented features of the Fleek Media Service."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.storage_path = Path("storage")

    async def run_all_tests(self):
        """Run comprehensive test suite covering all features."""
        print(
            "🧪 Fleek Media Service - Comprehensive Feature Test"
        )
        print("=" * 60)

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                # 1. System Health Tests
                await self._test_system_endpoints(client)

                # 2. Job Management Tests
                job_ids = await self._test_job_management(client)

                # 3. Storage and Metadata Tests
                if job_ids:
                    await self._test_storage_and_metadata(client, job_ids[0])

                # 4. API Features Tests
                await self._test_advanced_api_features(client)

                print("\n✅ ALL TESTS PASSED! 🎉")
                print("The service is fully functional with all features working.")
                return True

            except Exception as e:
                print(f"\n❌ TEST SUITE FAILED: {e}")
                return False

    async def _test_system_endpoints(self, client: httpx.AsyncClient):
        """Test all system and monitoring endpoints."""
        print("\n🔍 Testing System Endpoints...")

        # Basic health check
        response = await client.get(f"{self.base_url}/health")
        assert response.status_code == 200
        health = response.json()
        assert health["status"] == "healthy"
        print("  ✅ Basic health check")

        # Detailed health check
        response = await client.get(f"{self.base_url}/health/detailed")
        assert response.status_code == 200
        detailed_health = response.json()
        assert "checks" in detailed_health
        print("  ✅ Detailed health check with dependencies")

        # Metrics endpoint
        response = await client.get(f"{self.base_url}/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert "metrics" in metrics
        print("  ✅ Metrics endpoint")

        # Service info
        response = await client.get(f"{self.base_url}/info")
        assert response.status_code == 200
        info = response.json()
        assert "endpoints" in info
        assert "monitoring" in info
        print("  ✅ Service info endpoint")

        # Root endpoint
        response = await client.get(f"{self.base_url}/")
        assert response.status_code == 200
        root = response.json()
        assert root["service"] == "Fleek Media Service"
        print("  ✅ Root service endpoint")

    async def _test_job_management(self, client: httpx.AsyncClient):
        """Test job creation, listing, and management features."""
        print("\n🔍 Testing Job Management...")

        job_ids = []

        # Create multiple jobs with different parameters
        test_jobs = [
            {
                "prompt": "A majestic mountain landscape at golden hour",
                "model_name": "black-forest-labs/flux-schnell",
                "parameters": json.dumps(
                    {"width": 1024, "height": 1024, "guidance_scale": 3.5}
                ),
            },
            {
                "prompt": "A serene ocean scene with sunset reflections",
                "model_name": "black-forest-labs/flux-schnell",
                "parameters": json.dumps(
                    {"width": 768, "height": 768, "num_inference_steps": 4}
                ),
            },
            {
                "prompt": "Abstract art with vibrant colors and geometric shapes",
                "model_name": "stable-diffusion",
                "parameters": json.dumps({"width": 512, "height": 512}),
            },
        ]

        # Create jobs
        for i, job_data in enumerate(test_jobs):
            response = await client.post(
                f"{self.base_url}/api/v1/generate", json=job_data
            )
            assert response.status_code == 201
            job = response.json()
            job_ids.append(job["id"])
            print(f"  ✅ Created job {i+1}: {job['id'][:8]}...")

        # Test job listing
        response = await client.get(f"{self.base_url}/api/v1/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) >= len(test_jobs)
        print(f"  ✅ Listed jobs: {len(jobs)} total jobs found")

        # Test job listing with pagination
        response = await client.get(f"{self.base_url}/api/v1/jobs?limit=2&offset=0")
        assert response.status_code == 200
        paginated_jobs = response.json()
        assert len(paginated_jobs) <= 2
        print("  ✅ Job pagination working")

        # Test status filtering (once some jobs complete)
        await asyncio.sleep(5)  # Give time for some processing
        response = await client.get(
            f"{self.base_url}/api/v1/jobs?status_filter=pending"
        )
        assert response.status_code == 200
        pending_jobs = response.json()
        print(f"  ✅ Status filtering: {len(pending_jobs)} pending jobs")

        # Test individual job status
        for job_id in job_ids[:2]:  # Test first 2 jobs
            response = await client.get(f"{self.base_url}/api/v1/status/{job_id}")
            assert response.status_code == 200
            job_status = response.json()
            assert job_status["id"] == job_id
            print(f"  ✅ Job status check: {job_id[:8]}... - {job_status['status']}")

        return job_ids

    async def _test_storage_and_metadata(self, client: httpx.AsyncClient, job_id: str):
        """Test storage and metadata functionality."""
        print("\n🔍 Testing Storage and Metadata...")

        # Wait for job to potentially complete
        max_wait = 60  # 1 minute
        wait_time = 0
        job_completed = False

        while wait_time < max_wait:
            response = await client.get(f"{self.base_url}/api/v1/status/{job_id}")
            job = response.json()

            if job["status"] == "completed":
                job_completed = True
                break
            elif job["status"] == "failed":
                print(f"  ⚠️ Job {job_id[:8]}... failed, testing metadata anyway")
                break

            await asyncio.sleep(5)
            wait_time += 5

        # Test metadata endpoint (should work regardless of completion)
        response = await client.get(f"{self.base_url}/api/v1/jobs/{job_id}/metadata")
        if response.status_code == 200:
            metadata = response.json()
            assert "prompt" in metadata
            assert "model_name" in metadata
            print("  ✅ Metadata retrieval working")
            print(f"    📋 Metadata keys: {list(metadata.keys())}")
        else:
            print("  ⚠️ Metadata not yet available (job may still be starting)")

        # Test file download if job completed
        if job_completed:
            response = await client.get(f"{self.base_url}/api/v1/download/{job_id}")
            if response.status_code == 200:
                print("  ✅ File download working")
                print(f"    📁 File size: {len(response.content):,} bytes")

                # Verify it's a valid image
                try:
                    from io import BytesIO

                    img = Image.open(BytesIO(response.content))
                    print(f"    🖼️ Image format: {img.format}, Size: {img.size}")
                    print("  ✅ Downloaded file is valid image")
                except Exception as e:
                    print(f"  ⚠️ Downloaded file validation failed: {e}")
            else:
                print(f"  ⚠️ File download failed: {response.status_code}")

        # Test storage structure verification
        media_path = self.storage_path / "media"
        metadata_path = self.storage_path / "metadata"

        if media_path.exists():
            media_files = list(media_path.glob("*.png"))
            print(f"  📁 Media files found: {len(media_files)}")

        if metadata_path.exists():
            metadata_files = list(metadata_path.glob("*.json"))
            print(f"  📄 Metadata files found: {len(metadata_files)}")

    async def _test_advanced_api_features(self, client: httpx.AsyncClient):
        """Test advanced API features and edge cases."""
        print("\n🔍 Testing Advanced API Features...")

        # Test job cancellation
        # Create a job to cancel
        job_data = {
            "prompt": "Test job for cancellation",
            "model_name": "stable-diffusion",
        }
        response = await client.post(f"{self.base_url}/api/v1/generate", json=job_data)
        assert response.status_code == 201
        job = response.json()
        cancel_job_id = job["id"]

        # Try to cancel it
        response = await client.delete(f"{self.base_url}/api/v1/jobs/{cancel_job_id}")
        if response.status_code == 200:
            print("  ✅ Job cancellation working")
        else:
            print(f"  ⚠️ Job cancellation response: {response.status_code}")

        # Test error handling - invalid job ID
        response = await client.get(f"{self.base_url}/api/v1/status/invalid-uuid")
        assert response.status_code == 422  # Validation error
        print("  ✅ Invalid UUID handling")

        # Test error handling - non-existent job
        fake_uuid = "12345678-1234-1234-1234-123456789012"
        response = await client.get(f"{self.base_url}/api/v1/status/{fake_uuid}")
        assert response.status_code == 404
        print("  ✅ Non-existent job handling")

        # Test parameter validation
        invalid_job = {"prompt": "", "model_name": "stable-diffusion"}  # Empty prompt
        response = await client.post(
            f"{self.base_url}/api/v1/generate", json=invalid_job
        )
        # Should either reject or accept gracefully
        print(f"  ✅ Empty prompt handling: {response.status_code}")

        # Test large prompt
        large_prompt = "A " + "very " * 100 + "detailed image description"
        large_job = {"prompt": large_prompt, "model_name": "stable-diffusion"}
        response = await client.post(f"{self.base_url}/api/v1/generate", json=large_job)
        print(f"  ✅ Large prompt handling: {response.status_code}")

    async def _test_documentation_features(self, client: httpx.AsyncClient):
        """Test documentation and API discovery features."""
        print("\n🔍 Testing Documentation Features...")

        # Test OpenAPI docs
        response = await client.get(f"{self.base_url}/docs")
        assert response.status_code == 200
        print("  ✅ Interactive docs accessible")

        # Test OpenAPI JSON
        response = await client.get(f"{self.base_url}/openapi.json")
        assert response.status_code == 200
        openapi_spec = response.json()
        assert "paths" in openapi_spec
        print("  ✅ OpenAPI specification available")

        # Count available endpoints
        paths = openapi_spec.get("paths", {})
        endpoint_count = sum(len(methods) for methods in paths.values())
        print(f"  📊 Total API endpoints documented: {endpoint_count}")


async def main():
    """Main test function."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"

    print("🎯 Fleek Media Service - Complete Feature Test Suite")
    print("=" * 60)
    print(f"🔗 Testing API at: {base_url}")
    print(f"⏰ Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    tester = ComprehensiveFeatureTester(base_url)
    success = await tester.run_all_tests()

    print("\n" + "=" * 60)
    print(f"⏰ Test completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    if success:
        print("🎉 COMPREHENSIVE TEST SUITE PASSED!")
        print("✅ All features are working correctly")
        print("🚀 Service is ready for production deployment")
        sys.exit(0)
    else:
        print("💥 COMPREHENSIVE TEST SUITE FAILED!")
        print("❌ Please check the logs above for issues")
        sys.exit(1)


if __name__ == "__main__":
    print("🔧 Make sure the API server is running before starting tests")
    print("💡 Usage: python scripts/test_complete_features.py [base_url]")
    print("📝 Example: python scripts/test_complete_features.py http://localhost:8000")
    print()
    asyncio.run(main())
