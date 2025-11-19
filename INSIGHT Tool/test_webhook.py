"""
Simple test script to verify webhook endpoint is working
"""
import requests
import json

# Test data - minimal GitHub webhook payload
test_payload = {
    "action": "opened",
    "repository": {
        "full_name": "test/repo"
    }
}

headers = {
    "Content-Type": "application/json",
    "X-GitHub-Event": "ping"
}

try:
    response = requests.post(
        "http://127.0.0.1:5000/",
        json=test_payload,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✓ Webhook endpoint is working correctly!")
    else:
        print("\n✗ Webhook endpoint returned an error")
        
except Exception as e:
    print(f"Error testing webhook: {e}")
