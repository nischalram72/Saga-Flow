import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request, status
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse
# pyrefly: ignore [missing-import]
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.db.database import engine, Base
from app.routes import inventory
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # We will let Alembic handle migrations
    from app.models.inventory import Inventory
    # pyrefly: ignore [missing-import]
    from sqlalchemy.future import select
    # pyrefly: ignore [missing-import]
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.database import AsyncSessionLocal
    
    # Seed 10 sample products if table is empty
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Inventory).limit(1))
            if result.scalar_one_or_none() is None:
                for i in range(1, 11):
                    prod = Inventory(product_id=f"prod-{i}", available_qty=100, reserved_qty=0)
                    session.add(prod)
                await session.commit()
                print("Seeded 10 products into inventory.")
    except Exception as e:
        print("Could not seed DB, tables might not exist yet:", e)
        
    from app.core.rabbitmq import rabbitmq_client
    from app.core.consumer import start_consumer
    await rabbitmq_client.connect()
    start_consumer()
    
    yield
    
    await rabbitmq_client.close()
    await engine.dispose()

app = FastAPI(title="Inventory Service", lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    sanitized_errors = []
    for err in exc.errors():
        err_copy = err.copy()
        if 'ctx' in err_copy and 'error' in err_copy['ctx']:
            err_copy['ctx']['error'] = str(err_copy['ctx']['error'])
        sanitized_errors.append(err_copy)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Validation Error", "details": sanitized_errors}
    )

from fastapi.middleware.cors import CORSMiddleware
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryResponse
from sqlalchemy.future import select
from app.db.database import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inventory.router)

@app.get("/products", response_model=List[InventoryResponse])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Inventory).order_by(Inventory.product_id))
    return result.scalars().all()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "inventory"}

