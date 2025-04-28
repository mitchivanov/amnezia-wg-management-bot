from pydantic import BaseModel, Field
from typing import Optional

class GenerateKeyRequest(BaseModel):
    server_id: int = Field(..., description="ID сервера для генерации ключа")

class GenerateKeyResponse(BaseModel):
    amneziawg_key: str = Field(..., description="AmneziaWG-ключ (vpn://)")
    conf: str = Field(..., description="WireGuard .conf файл клиента")

class AddServerRequest(BaseModel):
    host: str = Field(..., description="IP-адрес или доменное имя сервера")
    port: int = Field(22, description="SSH порт сервера")
    username: str = Field(..., description="Имя пользователя для SSH")
    auth_type: str = Field(..., description="Тип аутентификации: 'password' или 'key'")
    password: Optional[str] = Field(None, description="Пароль для SSH (если используется)")
    key_path: Optional[str] = Field(None, description="Путь к приватному ключу (если используется)")
    wg_config_file: Optional[str] = Field(None, description="Путь к конфигу WireGuard на сервере")
    # endpoint не указывается пользователем, вычисляется автоматически

class AddServerResponse(BaseModel):
    id: int = Field(..., description="ID добавленного сервера")
    server_public_key: Optional[str] = Field(None, description="Публичный ключ WireGuard сервера")
