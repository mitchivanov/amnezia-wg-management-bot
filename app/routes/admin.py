from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_session
from service.server_service import ServerService
from schemas.admin import GenerateKeyRequest, GenerateKeyResponse, AddServerRequest, AddServerResponse

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/server/{server_id}/generate-key", response_model=GenerateKeyResponse)
async def generate_key(
    server_id: int = Path(..., description="ID сервера для генерации ключа"),
    session: AsyncSession = Depends(get_session)
):
    service = ServerService(session)
    amneziawg_key, conf = await service.generate_wg_key_for_server(server_id)
    if not amneziawg_key or not conf:
        raise HTTPException(status_code=404, detail="Сервер не найден или не удалось получить ключ")
    return GenerateKeyResponse(amneziawg_key=amneziawg_key, conf=conf)

@router.post("/server/add", response_model=AddServerResponse)
async def add_server(
    request: AddServerRequest,
    session: AsyncSession = Depends(get_session)
):
    service = ServerService(session)
    server = await service.add_server(request)
    if not server:
        raise HTTPException(status_code=500, detail="Не удалось добавить сервер")
    return AddServerResponse(id=server.id, server_public_key=server.server_public_key)
