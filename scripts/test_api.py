#!/usr/bin/env python3
"""
API testing script for Fleek Media Service.
Provides manual testing of the API endpoints.
"""

import asyncio
import json
import sys
from uuid import UUID

import httpx


async def test_api():
    """Test the main API endpoints."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        try:
            # Test health check
            print("🔍 Testing health check...")
            response = await client.get(f"{base_url}/health")
            print(f"Health check: {response.status_code} - {response.json()}")

            # Test service info
            print("\n🔍 Testing service info...")
            response = await client.get(f"{base_url}/info")
            print(f"Service info: {response.status_code}")
            print(json.dumps(response.json(), indent=2))

            # Test job creation
            print("\n🔍 Testing job creation...")
            job_data = {
                "prompt": "A beautiful sunset over mountains",
                "model_name": "stable-diffusion",
                "parameters": '{"width": 1024, "height": 1024}',
            }

            response = await client.post(f"{base_url}/api/v1/generate", json=job_data)

            if response.status_code == 201:
                job = response.json()
                job_id = job["id"]
                print(f"✅ Job created successfully: {job_id}")
                print(f"Status: {job['status']}")

                # Test status checking
                print(f"\n🔍 Testing status check for job {job_id}...")
                for i in range(3):
                    await asyncio.sleep(2)
                    response = await client.get(f"{base_url}/api/v1/status/{job_id}")

                    if response.status_code == 200:
                        job_status = response.json()
                        print(f"Attempt {i+1}: Status = {job_status['status']}")

                        if job_status["status"] == "completed":
                            print(
                                f"✅ Job completed! Result URL: {job_status.get('result_url')}"
                            )
                            break
                        elif job_status["status"] == "failed":
                            print(f"❌ Job failed: {job_status.get('error_message')}")
                            break
                    else:
                        print(f"❌ Status check failed: {response.status_code}")
                        break

            else:
                print(f"❌ Job creation failed: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"❌ Test failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    print("🚀 Starting API tests...")
    print("Make sure the API server is running on http://localhost:8000")
    asyncio.run(test_api())
    print("\n✅ API tests completed!")
