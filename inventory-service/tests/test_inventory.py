import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.routes.inventory import reserve_inventory, release_inventory
from app.schemas.inventory import ReserveRequest, ReleaseRequest, ReserveItem
from app.models.inventory import Inventory, Reservation, ReservationStatus

@pytest.mark.asyncio
async def test_reserve_inventory_success():
    # Setup mock request
    request = ReserveRequest(order_id="order-123", items=[ReserveItem(product_id="prod-1", quantity=2)])
    
    # Setup mock DB session
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    
    # First execute is existing reservations check (return empty)
    # Second execute is fetching inventory item
    mock_inventory = Inventory(product_id="prod-1", available_qty=10, reserved_qty=0)
    
    mock_result_empty = MagicMock()
    mock_result_empty.scalars.return_value.all.return_value = []
    
    mock_result_item = MagicMock()
    mock_result_item.scalar_one_or_none.return_value = mock_inventory
    
    mock_db.execute.side_effect = [mock_result_empty, mock_result_item]
    
    # Mock redis to avoid actual connection
    with patch('app.routes.inventory.redis_client.get', new_callable=AsyncMock) as mock_redis_get, \
         patch('app.routes.inventory.redis_client.set', new_callable=AsyncMock) as mock_redis_set:
        
        mock_redis_get.return_value = None
        
        response = await reserve_inventory(request=request, db=mock_db)
        
        assert response["message"] == "Inventory reserved successfully"
        assert response["order_id"] == "order-123"
        
        # Verify math
        assert mock_inventory.available_qty == 8
        assert mock_inventory.reserved_qty == 2
        
        # Verify DB calls
        assert mock_db.add.called
        assert mock_db.commit.called

@pytest.mark.asyncio
async def test_reserve_inventory_insufficient_stock():
    request = ReserveRequest(order_id="order-123", items=[ReserveItem(product_id="prod-1", quantity=15)])
    mock_db = AsyncMock()
    
    mock_inventory = Inventory(product_id="prod-1", available_qty=10, reserved_qty=0)
    
    mock_result_empty = MagicMock()
    mock_result_empty.scalars.return_value.all.return_value = []
    
    mock_result_item = MagicMock()
    mock_result_item.scalar_one_or_none.return_value = mock_inventory
    
    mock_db.execute.side_effect = [mock_result_empty, mock_result_item]
    
    with patch('app.routes.inventory.redis_client.get', new_callable=AsyncMock) as mock_redis_get, \
         patch('app.routes.inventory.redis_client.set', new_callable=AsyncMock) as mock_redis_set:
        
        mock_redis_get.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await reserve_inventory(request=request, db=mock_db)
            
        assert exc_info.value.status_code == 400
        assert "Insufficient stock" in exc_info.value.detail
        
        # Verify math unchanged
        assert mock_inventory.available_qty == 10
        assert mock_inventory.reserved_qty == 0

@pytest.mark.asyncio
async def test_release_inventory_success():
    request = ReleaseRequest(order_id="order-123")
    mock_db = AsyncMock()
    
    mock_reservation = Reservation(id="res-1", order_id="order-123", product_id="prod-1", qty=2, status=ReservationStatus.CONFIRMED)
    mock_inventory = Inventory(product_id="prod-1", available_qty=8, reserved_qty=2)
    
    mock_res_result = MagicMock()
    mock_res_result.scalars.return_value.all.return_value = [mock_reservation]
    
    mock_inv_result = MagicMock()
    mock_inv_result.scalar_one_or_none.return_value = mock_inventory
    
    mock_db.execute.side_effect = [mock_res_result, mock_inv_result]
    
    response = await release_inventory(request=request, db=mock_db)
    
    assert response["message"] == "Inventory released successfully"
    
    # Verify math
    assert mock_inventory.available_qty == 10
    assert mock_inventory.reserved_qty == 0
    assert mock_reservation.status == ReservationStatus.CANCELLED
    
    assert mock_db.commit.called
