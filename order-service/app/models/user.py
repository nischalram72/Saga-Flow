import enum
import uuid
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Enum, DateTime
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.database import Base

class Role(str, enum.Enum):
    customer = "customer"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.customer)
    created_at = Column(DateTime, default=datetime.utcnow)
