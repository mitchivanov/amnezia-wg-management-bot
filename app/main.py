from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_200_OK
import logging
import uvicorn
import os
import asyncio
from contextlib import asynccontextmanager

# Импортируем роутеры
from routes.admin import router as admin_router
from database.database import init_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("amnezia-wg-management")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, выполняемый при запуске приложения
    logger.info("Инициализация базы данных...")
    try:
        await init_db()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise
    
    yield  # Здесь приложение работает
    
    # Код, выполняемый при остановке приложения
    logger.info("Приложение завершает работу")

# Конфигурация приложения
app = FastAPI(
    title="Amnezia WG Management API",
    description="API для управления Amnezia WireGuard серверами и пользователями.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=False,
    lifespan=lifespan
)

# CORS (разрешить только нужные домены в проде)
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip для экономии трафика
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted hosts (пример: только ваш домен и localhost)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "yourdomain.com"])

# HTTPS redirect (если нужен https)
if os.getenv("FORCE_HTTPS", "0") == "1":
    app.add_middleware(HTTPSRedirectMiddleware)

# Session middleware (если нужны сессии)
# app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "supersecret"))

# Healthcheck endpoint
@app.get("/health", tags=["health"])
async def health():
    return JSONResponse(status_code=HTTP_200_OK, content={"status": "ok"})

# Интеграция роутеров
app.include_router(admin_router)

# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # В проде reload=False
        workers=4      # Количество воркеров подберите под сервер
    )
