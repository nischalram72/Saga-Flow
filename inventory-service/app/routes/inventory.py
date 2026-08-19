# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select
from typing import List
import os
import json
# pyrefly: ignore [missing-import]
import redis.asyncio as redis

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url, decode_responses=True)

from app.db.database import get_db
from app.models.inventory import Inventory, Reservation, ReservationStatus
from app.schemas.inventory import ReserveRequest, ReleaseRequest, ReservationResponse
from app.api.deps import verify_service_key

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(verify_service_key)])

@router.post("/reserve", status_code=status.HTTP_200_OK)
async def reserve_inventory(request: ReserveRequest, db: AsyncSession = Depends(get_db)):
    # Check Redis cache for idempotency
    cached_response = await redis_client.get(f"idempotency:{request.order_id}")
    if cached_response:
        data = json.loads(cached_response)
        if data.get("status") == "FAILED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=data.get("detail", "Inventory reservation failed previously")
            )
        return data

    # Check idempotency in DB (fallback)
    existing_reservations_result = await db.execute(
        select(Reservation).where(Reservation.order_id == request.order_id)
    )
    existing_reservations = existing_reservations_result.scalars().all()
    if existing_reservations:
        response_data = {"message": "Inventory reserved successfully", "order_id": request.order_id}
        await redis_client.set(f"idempotency:{request.order_id}", json.dumps(response_data), ex=86400)
        return response_data

    reservations = []
    
    # Process each item in the reserve request
    for item in request.items:
        # Fetch the inventory item with a row-level lock
        result = await db.execute(
            select(Inventory).where(Inventory.product_id == item.product_id).with_for_update()
        )
        inventory = result.scalar_one_or_none()
        
        if not inventory:
            fail_data = {"status": "FAILED", "detail": f"Product {item.product_id} not found"}
            await redis_client.set(f"idempotency:{request.order_id}", json.dumps(fail_data), ex=86400)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=fail_data["detail"]
            )
            
        if inventory.available_qty < item.quantity:
            fail_data = {"status": "FAILED", "detail": f"Insufficient stock for product {item.product_id}. Available: {inventory.available_qty}"}
            await redis_client.set(f"idempotency:{request.order_id}", json.dumps(fail_data), ex=86400)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=fail_data["detail"]
            )
            
        # Update stock
        inventory.available_qty -= item.quantity
        inventory.reserved_qty += item.quantity
        
        # Create reservation record
        reservation = Reservation(
            order_id=request.order_id,
            product_id=item.product_id,
            qty=item.quantity,
            status=ReservationStatus.CONFIRMED
        )
        db.add(reservation)
        reservations.append(reservation)
        
    await db.commit()
    
    response_data = {"message": "Inventory reserved successfully", "order_id": request.order_id}
    await redis_client.set(f"idempotency:{request.order_id}", json.dumps(response_data), ex=86400)
    
    return response_data

@router.post("/release", status_code=status.HTTP_200_OK)
async def release_inventory(request: ReleaseRequest, db: AsyncSession = Depends(get_db)):
    # Find all reservations for this order
    result = await db.execute(
        select(Reservation)
        .where(Reservation.order_id == request.order_id)
        .where(Reservation.status == ReservationStatus.CONFIRMED)
    )
    reservations = result.scalars().all()
    
    if not reservations:
        return {"message": "No active reservations found for this order"}
        
    for res in reservations:
        # Fetch inventory with lock
        inv_result = await db.execute(
            select(Inventory).where(Inventory.product_id == res.product_id).with_for_update()
        )
        inventory = inv_result.scalar_one_or_none()
        
        if inventory:
            # Revert the reserved quantities
            inventory.reserved_qty -= res.qty
            inventory.available_qty += res.qty
            
        # Mark reservation as cancelled
        res.status = ReservationStatus.CANCELLED
        
    await db.commit()
    return {"message": "Inventory released successfully"}
