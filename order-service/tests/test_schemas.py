import pytest
from pydantic import ValidationError
from app.schemas.order import OrderCreate, OrderItemCreate

def test_order_create_valid():
    order = OrderCreate(
        user_id="user-123",
        total_amount=100.0,
        items=[
            OrderItemCreate(product_id="prod-1", quantity=2, price=50.0)
        ]
    )
    assert order.total_amount == 100.0
    assert len(order.items) == 1

def test_order_create_invalid_total_amount():
    with pytest.raises(ValidationError) as exc_info:
        OrderCreate(
            user_id="user-123",
            total_amount=100.0,
            items=[
                OrderItemCreate(product_id="prod-1", quantity=2, price=40.0)
            ]
        )
    assert "total_amount (100.0) does not match sum of items (80.0)" in str(exc_info.value)

def test_order_item_invalid_quantity():
    with pytest.raises(ValidationError) as exc_info:
        OrderItemCreate(product_id="prod-1", quantity=0, price=50.0)
    assert "greater than 0" in str(exc_info.value)

def test_order_item_invalid_price():
    with pytest.raises(ValidationError) as exc_info:
        OrderItemCreate(product_id="prod-1", quantity=1, price=-10.0)
    assert "greater than 0" in str(exc_info.value)

def test_order_create_empty_items():
    with pytest.raises(ValidationError) as exc_info:
        OrderCreate(
            user_id="user-123",
            total_amount=100.0,
            items=[]
        )
    assert "List should have at least 1 item after validation" in str(exc_info.value)
