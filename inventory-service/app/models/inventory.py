import uuid
import enum
from datetime import datetime
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Integer, DateTime, Enum
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

class ReservationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class Inventory(Base):
    __tablename__ = "inventory"

    product_id = Column(String, primary_key=True)
    available_qty = Column(Integer, default=0, nullable=False)
    reserved_qty = Column(Integer, default=0, nullable=False)

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(String, nullable=False, index=True)
    product_id = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    status = Column(Enum(ReservationStatus), default=ReservationStatus.PENDING, nullable=False)
    expires_at = Column(DateTime, nullable=True)
