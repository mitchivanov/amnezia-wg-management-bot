from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from models.server_models import SSHServerConfig

class ServerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_server(self, server: SSHServerConfig) -> SSHServerConfig:
        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def get_server_by_id(self, server_id: int) -> Optional[SSHServerConfig]:
        result = await self.db.execute(select(SSHServerConfig).where(SSHServerConfig.id == server_id))
        return result.scalars().first()

    async def get_all_servers(self) -> List[SSHServerConfig]:
        result = await self.db.execute(select(SSHServerConfig))
        return result.scalars().all()

    async def update_server(self, server_id: int, **kwargs) -> Optional[SSHServerConfig]:
        server = await self.get_server_by_id(server_id)
        if not server:
            return None
        for key, value in kwargs.items():
            if hasattr(server, key):
                setattr(server, key, value)
        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def delete_server(self, server_id: int) -> bool:
        server = await self.get_server_by_id(server_id)
        if not server:
            return False
        await self.db.delete(server)
        await self.db.commit()
        return True
