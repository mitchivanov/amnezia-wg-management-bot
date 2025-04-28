from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class SSHServerConfig(Base):
    __tablename__ = 'ssh_server_configs'

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор сервера
    host = Column(String, nullable=False)  # IP-адрес или доменное имя сервера
    port = Column(Integer, nullable=False, default=22)  # SSH порт
    username = Column(String, nullable=False)  # Имя пользователя для SSH
    auth_type = Column(String, nullable=False)  # Тип аутентификации: 'password' или 'key'
    password = Column(String, nullable=True)  # Пароль (если используется)
    key_path = Column(String, nullable=True)  # Путь к приватному ключу (если используется)
    wg_config_file = Column(String, nullable=True)  # Путь к конфигу WireGuard
    endpoint = Column(String, nullable=True)  # Публичный endpoint сервера (IP:PORT или домен:порт)
    server_public_key = Column(String, nullable=True)  # Публичный ключ WireGuard сервера
    is_active = Column(Boolean, default=True)  # Флаг активности сервера

    def __repr__(self):
        return f"<SSHServerConfig(id={self.id}, host='{self.host}', username='{self.username}', server_public_key='{self.server_public_key}')>"

    @staticmethod
    def from_schema(schema):
        return SSHServerConfig(
            host=schema.host,
            port=schema.port,
            username=schema.username,
            auth_type=schema.auth_type,
            password=schema.password,
            key_path=schema.key_path,
            wg_config_file=schema.wg_config_file,
            endpoint=schema.endpoint,
            server_public_key=getattr(schema, 'server_public_key', None),
        )

