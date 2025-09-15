from fastapi import HTTPException

# Dummy API key list for demo
API_KEYS = ["demo_key_123", "test_key_456"]

def verify_api_key(api_key: str):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key
