import asyncio
from sqlalchemy.future import select
from sqlalchemy import update
from app.db.database import AsyncSessionLocal
from app.models.inventory import Inventory

async def fix_negative_reserved_qty():
    async with AsyncSessionLocal() as session:
        # Fetch products with negative reserved_qty
        result = await session.execute(select(Inventory).where(Inventory.reserved_qty < 0))
        products = result.scalars().all()
        
        for p in products:
            print(f"Fixing {p.product_id}: reserved_qty={p.reserved_qty}")
            p.reserved_qty = 0
            
        if products:
            await session.commit()
            print("Successfully reset negative reserved_qty values to 0.")
        else:
            print("No negative reserved_qty values found.")

if __name__ == "__main__":
    asyncio.run(fix_negative_reserved_qty())
