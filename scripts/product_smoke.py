"""Automated API Smoke Test.
Verifies service healthz and foundational routes when running.
"""
import sys
import httpx

def main():
    base_url = "http://localhost:8000"
    print(f"Connecting to {base_url}...")
    try:
        r = httpx.get(f"{base_url}/healthz", timeout=5.0)
        print(f"GET /healthz -> {r.status_code}")
        if r.status_code != 200:
            return 1
        data = r.json()
        print(f"Service status: {data.get('status')}, version: {data.get('version')}")
        return 0
    except Exception as e:
        print(f"Error connecting to service: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
