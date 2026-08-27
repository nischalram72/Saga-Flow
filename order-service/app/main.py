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
# pyrefly: ignore [missing-import]
from contextlib import asynccontextmanager
# pyrefly: ignore [missing-import]
from app.db.database import engine, Base
# pyrefly: ignore [missing-import]
from app.routes import orders, auth
import os

from app.core.rabbitmq import rabbitmq_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.consumer import start_consumer
    from app.db.database import AsyncSessionLocal
    from sqlalchemy.future import select
    from app.models.user import User, Role
    from app.core.security import get_password_hash
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == "impressio2005@gmail.com"))
            admin = result.scalar_one_or_none()
            if not admin:
                admin_user = User(
                    email="impressio2005@gmail.com",
                    hashed_password=get_password_hash("Anitha@15"),
                    role=Role.admin
                )
                session.add(admin_user)
                await session.commit()
                print("Seeded admin user.")
    except Exception as e:
        print("Could not seed admin user:", e)

    await rabbitmq_client.connect()
    start_consumer()
    yield
    await rabbitmq_client.close()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Order Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        err.pop('ctx', None)
        errors.append(err)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Validation Error", "details": errors}
    )

app.include_router(orders.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Order Service"}
