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
from app.db.database import engine
from app.routes import payments

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.rabbitmq import rabbitmq_client
    from app.core.consumer import start_consumer
    await rabbitmq_client.connect()
    start_consumer()
    
    yield
    
    await rabbitmq_client.close()
    await engine.dispose()

app = FastAPI(title="Payment Service", lifespan=lifespan)

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

app.include_router(payments.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "payment"}

