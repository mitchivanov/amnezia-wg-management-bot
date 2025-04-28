from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import AsyncGenerator
import os
import logging

logger = logging.getLogger("amnezia-wg-management")

# Получаем URL подключения из переменной окружения или используем значение по умолчанию
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@db:5432/dbname")

# Создаем асинхронный движок для PostgreSQL
engine = create_async_engine(DATABASE_URL, echo=False)

# Настраиваем асинхронную сессию
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Создаем базовый класс для моделей
Base = declarative_base()

async def init_db():
    try:
        from models.server_models import Base as ServerBase
        from models.user_models import Base as UserBase
        
        logger.info(f"Инициализация базы данных по URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0], '***')}")
        
        async with engine.begin() as conn:
            # Создаем таблицы из всех моделей
            await conn.run_sync(ServerBase.metadata.create_all)
            await conn.run_sync(UserBase.metadata.create_all)
        
        logger.info("Таблицы успешно созданы")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_db_session() -> AsyncSession:
    """
    Функция для прямого получения сессии базы данных.
    Для использования в сервисах без Depends.
    """
    return async_session()
