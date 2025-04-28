import logging
import asyncssh
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.server_repo import ServerRepository
from models.server_models import SSHServerConfig
from typing import Optional
from service.awg_utils import encode_vpn_conf
import time
import subprocess
import base64
import re

logger = logging.getLogger(__name__)

class ServerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ServerRepository(db)

    async def add_server(self, schema) -> Optional[SSHServerConfig]:
        server = SSHServerConfig.from_schema(schema)
        # Получаем server.conf из контейнера
        wg_config_file = server.wg_config_file or "/opt/amnezia/awg/wg0.conf"
        get_conf_cmd = f"docker exec -i amnezia-awg cat {wg_config_file}"
        conf_text = await self._run_ssh_command(server, get_conf_cmd)
        server_public_key = None
        listen_port = None
        if conf_text:
            m = re.search(r"^PrivateKey\s*=\s*(.+)$", conf_text, re.MULTILINE)
            if m:
                private_key = m.group(1).strip()
                pubkey_cmd = f"echo '{private_key}' | docker exec -i amnezia-awg wg pubkey"
                pubkey = await self._run_ssh_command(server, pubkey_cmd)
                if pubkey:
                    server_public_key = pubkey.strip()
            m_port = re.search(r"^ListenPort\s*=\s*(\d+)$", conf_text, re.MULTILINE)
            if m_port:
                listen_port = m_port.group(1).strip()
        # Склеиваем endpoint как <IP сервера>:<ListenPort>
        endpoint = f"{server.host}:{listen_port}" if listen_port else server.host
        server.endpoint = endpoint
        server.server_public_key = server_public_key
        server = await self.repo.add_server(server)
        logger.info(f"Добавлен новый сервер: {server}")
        return server

    async def _run_ssh_command(self, server: SSHServerConfig, command: str) -> Optional[str]:
        logger.info(f"Попытка подключения к серверу {server.host}:{server.port} как {server.username} для выполнения команды: {command}")
        try:
            conn_params = {
                'host': server.host,
                'port': server.port,
                'username': server.username,
                'known_hosts': None
            }
            if server.auth_type == 'password':
                conn_params['password'] = server.password
            elif server.auth_type == 'key':
                conn_params['client_keys'] = [server.key_path]
            else:
                logger.error(f"Неизвестный тип аутентификации: {server.auth_type}")
                raise ValueError('Unknown auth_type')
            async with asyncssh.connect(**conn_params) as conn:
                logger.info(f"Успешное SSH-подключение к {server.host}:{server.port}")
                result = await conn.run(command, check=True)
                if result.stderr:
                    logger.error(f"Ошибка при выполнении команды на сервере {server.host}: {result.stderr}")
                    raise Exception(f'SSH error: {result.stderr}')
                logger.info(f"Команда '{command}' успешно выполнена на сервере {server.host}")
                return result.stdout.strip()
        except Exception as e:
            logger.exception(f"Ошибка SSH при работе с сервером {server.host}: {e}")
            return None

    def _generate_unique_client_ip(self) -> str:
        # Простейшая генерация IP на основе времени (для демо, не для продакшена)
        octet = 2 + int(time.time()) % 253
        return f"10.8.1.{octet}/32"

    async def generate_wg_key_for_server(self, server_id: int) -> tuple:
        logger.info(f"Запрос на генерацию AmneziaWG-ключа для сервера с id={server_id}")
        server = await self.repo.get_server_by_id(server_id)
        if not server:
            logger.error(f"Сервер с id={server_id} не найден в базе данных")
            return None, None
        # 1. Генерируем приватный ключ внутри контейнера
        private_key = await self._run_ssh_command(server, "docker exec -i amnezia-awg wg genkey")
        logger.info(f"Сгенерированный приватный ключ: {private_key}")
        if not private_key:
            logger.error("Не удалось сгенерировать приватный ключ внутри контейнера")
            return None, None
        # 2. Генерируем публичный ключ внутри контейнера
        public_key = await self._run_ssh_command(server, f"echo '{private_key}' | docker exec -i amnezia-awg wg pubkey")
        logger.info(f"Сгенерированный публичный ключ клиента: {public_key}")
        if not public_key:
            logger.error("Не удалось сгенерировать публичный ключ клиента внутри контейнера")
            return None, None
        # 3. Генерируем pre-shared key внутри контейнера
        psk = await self._run_ssh_command(server, "docker exec -i amnezia-awg wg genpsk")
        logger.info(f"Сгенерированный pre-shared key: {psk}")
        if not psk:
            logger.error("Не удалось сгенерировать pre-shared key внутри контейнера")
            return None, None
        # 4. Получаем публичный ключ сервера из базы
        server_pubkey = server.server_public_key
        logger.info(f"Публичный ключ сервера из базы: {server_pubkey}")
        if not server_pubkey:
            logger.error("Публичный ключ сервера отсутствует в базе. Проверьте этап добавления сервера!")
            return None, None
        # 5. Получаем ListenPort из wg0.conf внутри контейнера
        wg_config_file = server.wg_config_file or "/opt/amnezia/awg/wg0.conf"
        get_conf_cmd = f"docker exec -i amnezia-awg cat {wg_config_file}"
        conf_text = await self._run_ssh_command(server, get_conf_cmd)
        listen_port = None
        if conf_text:
            m = re.search(r"^ListenPort\s*=\s*(\d+)$", conf_text, re.MULTILINE)
            if m:
                listen_port = m.group(1).strip()
        logger.info(f"ListenPort из wg0.conf: {listen_port}")
        if not listen_port:
            logger.error("Не удалось получить ListenPort из wg0.conf!")
            return None, None
        # 6. Формируем endpoint строго как в референсе
        endpoint = server.endpoint
        # 7. Формируем .conf-файл
        client_ip = self._generate_unique_client_ip()
        additional_params = "Jc = 2\nJmin = 10\nJmax = 50\nS1 = 91\nS2 = 149\nH1 = 96800746\nH2 = 55774911\nH3 = 440992545\nH4 = 1000889014"
        conf = f"""[Interface]\nAddress = {client_ip}\nDNS = 1.1.1.1, 1.0.0.1\nPrivateKey = {private_key}\n{additional_params}\n[Peer]\nPublicKey = {server_pubkey}\nPresharedKey = {psk}\nAllowedIPs = 0.0.0.0/0, ::/0\nEndpoint = {endpoint}\nPersistentKeepalive = 25\n"""
        logger.info(f"Сгенерированный .conf-файл клиента:\n{conf}")
        # 8. Кодируем в AmneziaWG-ключ
        amneziawg_key = encode_vpn_conf(conf)
        logger.info(f"AmneziaWG-ключ успешно сгенерирован для сервера id={server_id}")
        return amneziawg_key, conf
