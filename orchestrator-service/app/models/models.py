import uuid
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.database import Base
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship

class SagaInstance(Base):
    __tablename__ = "saga_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(String, unique=True, nullable=False)
    current_step = Column(String, nullable=False)
    status = Column(String, nullable=False)
    simulate_payment_failure = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = relationship("SagaStep", back_populates="saga_instance")

class SagaStep(Base):
    __tablename__ = "saga_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    saga_id = Column(UUID(as_uuid=True), ForeignKey("saga_instances.id"), nullable=False)
    step_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    compensated_at = Column(DateTime, nullable=True)

    saga_instance = relationship("SagaInstance", back_populates="steps")
