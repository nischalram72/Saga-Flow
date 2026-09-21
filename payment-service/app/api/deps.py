import os
from fastapi import Header, HTTPException, status

SERVICE_KEY = os.getenv("SERVICE_KEY", "internal_secret_key_123")

async def verify_service_key(x_service_key: str = Header(None)):
    if x_service_key != SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Service-Key header"
        )
