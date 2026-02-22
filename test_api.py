import requests
import time
import sys

BASE_URL = "http://localhost:5000"

def test_pipeline():
    print("1. Health Check...")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"Status: {r.status_code}, Body: {r.json()}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("\n2. Starting Agribusiness Plan...")
    payload = {
        "message": "I have 5 acres of Black Soil in Dharwad, Karnataka. I have a borewell and 10 lakhs investment capacity. I want to grow vegetables."
    }
    r = requests.post(f"{BASE_URL}/api/plan", json=payload)
    if r.status_code != 200:
        print(f"Error starting plan: {r.text}")
        return
    
    job_id = r.json().get("job_id")
    print(f"Job ID: {job_id}")
    
    print("\n3. Streaming Results...")
    # Connect to stream
    with requests.get(f"{BASE_URL}/api/plan/{job_id}/stream", stream=True) as stream:
        for line in stream.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    print(f"Received: {data_str}")

if __name__ == "__main__":
    test_pipeline()
