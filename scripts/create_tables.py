import asyncio
from app.db.session import engine, Base
from app.models.user import User
from app.models.document import Document

async def go():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("All tables created successfully")

asyncio.run(go())