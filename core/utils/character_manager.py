import sys

sys.path.append("..")
import time
import asyncio
from typing import Dict, Optional, Callable, Coroutine, Any
from core.agents.graph_instance import LangGraphInstance
from core.agents.conversation_instance import ConversationInstance
from loguru import logger


class Character:
    def __init__(self, agent_instance, conversation_instance: ConversationInstance):
        self.agent_instance = agent_instance
        self.conversation_instance = conversation_instance
        self.last_heartbeat = time.time()
        self.heartbeat_count = 1
        self.callback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None

    def update_heartbeat(self):
        self.last_heartbeat = time.time()
        self.heartbeat_count += 1


class CharacterManager:
    def __init__(self, timeout: int = 60):
        self.timeout: int = timeout
        self._monitor_task: Optional[asyncio.Task] = None
        self.start_time: float = time.time()
        self._characters: Dict[int, Character] = {}
        self._hosted_characters: Dict[int, Character] = {}

    def add_character(
        self,
        character_id: int,
        agent_instance: LangGraphInstance,
        conversation_instance: ConversationInstance,
        callback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
    ) -> None:
        self._characters[character_id] = Character(
            agent_instance, conversation_instance
        )
        if callback:
            self._characters[character_id].callback = callback

    def host_character(self, character_id: int) -> None:
        if self.has_character(character_id):
            self._hosted_characters[character_id] = self._characters[character_id]
            self._characters.pop(character_id, None)

            async def schedule_removal():
                await asyncio.sleep(60 * 60)
                self.remove_character(character_id)

            asyncio.create_task(schedule_removal())

    def unhost_character(self, character_id: int) -> None:
        if self.has_hosted_character(character_id):
            self._characters[character_id] = self._hosted_characters[character_id]
            self._hosted_characters.pop(character_id, None)
            logger.info(f"🔄 Character {character_id} moved back to active characters")

    def remove_character(self, character_id: int) -> None:
        self._characters.pop(character_id, None)
        self._hosted_characters.pop(character_id, None)

    def get_character(self, character_id: int) -> Optional[Character]:
        if self.has_hosted_character(character_id):
            return self._hosted_characters[character_id]
        return self._characters.get(character_id, None)

    def has_character(self, character_id: int) -> bool:
        return character_id in self._characters

    def has_hosted_character(self, character_id: int) -> bool:
        return character_id in self._hosted_characters

    async def start_monitoring(self) -> None:
        self._monitor_task = asyncio.create_task(self._check_heartbeats())
        logger.info("🫀 Heartbeat monitoring started")

    async def _check_heartbeats(self) -> None:
        while True:
            # logger.info("🔍 Performing heartbeat check...")
            for character_id, character in self._characters.items():
                if time.time() - character.last_heartbeat > self.timeout:
                    logger.error(f"💔 Character {character_id} heartbeat timeout")
                    if character.callback:
                        await character.callback()
                    self.host_character(character_id)
            await asyncio.sleep(self.timeout / 2)

    async def get_status(self) -> Dict[str, Any]:
        active_characters = [
            {
                "character_id": character_id,
                "status": "active",
                "last_heartbeat_time": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(character.last_heartbeat)
                ),
                "heartbeat_count": character.heartbeat_count,
                "has_callback": character.callback is not None,
            }
            for character_id, character in self._characters.items()
        ]

        hosted_characters = [
            {
                "character_id": character_id,
                "status": "hosted",
                "last_heartbeat_time": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(character.last_heartbeat)
                ),
                "heartbeat_count": character.heartbeat_count,
                "has_callback": character.callback is not None,
            }
            for character_id, character in self._hosted_characters.items()
        ]

        return {
            "monitor_status": {
                "uptime_seconds": f"{int(time.time() - self.start_time)} seconds",
                "timeout_setting": f"{self.timeout} seconds",
                "check_interval": f"{self.timeout // 2} seconds",
                "total_count": len(self._characters),
                "active_count": len(active_characters),
                "hosted_count": len(hosted_characters),
            },
            "clients": {
                "active_characters": active_characters,
                "hosted_characters": hosted_characters,
            },
        }
