import asyncio
from sqlalchemy import text
from app.db.database import AsyncSessionLocal

async def add_check_constraint():
    async with AsyncSessionLocal() as session:
        try:
            # We add a check constraint directly using raw SQL
            await session.execute(text("ALTER TABLE inventory ADD CONSTRAINT chk_reserved_qty_nonnegative CHECK (reserved_qty >= 0);"))
            await session.commit()
            print("Successfully added check constraint.")
        except Exception as e:
            print("Error or constraint already exists:", e)

if __name__ == "__main__":
    asyncio.run(add_check_constraint())
