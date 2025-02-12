import sys

sys.path.append(".")
import yaml
import asyncio
import websockets
import ssl
import json
import os
from loguru import logger
from core.utils.llm_factory import llm_selector
from utils.character_manager import CharacterManager
from utils.web_monitor.routes import WebMonitor
from core.agent_srv.utils import save_token_consumption_to_db
from core.agents.graph_instance import LangGraphInstance
from core.agents.conversation_instance import ConversationInstance


class ConfigLoader:
    def __init__(self, environment):
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path, "r") as file:
            self.config = yaml.safe_load(file)[environment]

    def get(self, key):
        return self.config.get(key)


class AI_WS_Server:
    def __init__(self, config):
        self.character_manager = CharacterManager(timeout=60)
        self.web_monitor = WebMonitor(self.character_manager)
        self.config = config

    async def handler(self, websocket, path):
        character_id = None
        try:
            success, character_id, response = await self.initialize_connection(
                websocket
            )
            await websocket.send(response)
            if not success:
                logger.warning(
                    f"🔗 Failed to connect to remote websocket: {websocket.remote_address}"
                )
                return

            logger.info(
                f"🔗 Successfully connected to remote websocket: {websocket.remote_address}"
            )
            character = self.character_manager.get_character(character_id)
            agent_instance = character.agent_instance
            conversation_instance = character.conversation_instance

            agent_instance.log_message("received", json.loads(response))

            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    agent_instance.log_message("sent", data)

                    if data.get("messageName") == "heartbeat":
                        character.update_heartbeat()
                        heartbeat_response = self.create_message(
                            character_id, "heartbeat", 0, **{"status": "ok"}
                        )
                        await websocket.send(heartbeat_response)
                        agent_instance.log_message("received", json.loads(heartbeat_response))
                    else:
                        message_queue = agent_instance.state["message_queue"]
                        await asyncio.gather(
                            message_queue.put(data),
                            conversation_instance.listener(data),
                        )

                except websockets.ConnectionClosed as e:
                    logger.warning(f"🔗 Connection closed from {character_id}: {e}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                except Exception as e:
                    logger.error(f"❌ Error in message loop: {e}")
                    break
        finally:
            if character_id:
                self.character_manager.host_character(character_id)
                logger.info(f"🧹 Cleaned up resources for Character {character_id}")
            await websocket.close()

    async def initialize_connection(self, websocket):
        init_message = await websocket.recv()
        init_data = json.loads(init_message)
        character_id = init_data.get("characterId")
        message_name = init_data.get("messageName")
        message_code = init_data.get("messageCode")

        if not character_id:
            return (
                False,
                character_id,
                self.create_message(
                    character_id,
                    message_name,
                    message_code,
                    **{"result": False, "msg": "character init failed"},
                ),
            )

        if self.character_manager.has_character(character_id):
            return (
                False,
                character_id,
                self.create_message(
                    character_id,
                    message_name,
                    message_code,
                    **{"result": False, "msg": "character ID is active"},
                ),
            )

        if self.character_manager.has_hosted_character(character_id):
            self.character_manager.unhost_character(character_id)

        agent_instance = await LangGraphInstance.create(character_id, websocket)

        conversation_instance = await ConversationInstance.create(
            character_id, websocket
        )

        self.character_manager.add_character(
            character_id, agent_instance, conversation_instance
        )

        agent_instance.log_message("sent", init_data)

        return (
            True,
            character_id,
            self.create_message(
                character_id,
                message_name,
                message_code,
                **{"result": True, "msg": "character init success"},
            ),
        )

    def create_message(self, character_id, message_name, message_code, **kwargs):
        return json.dumps(
            {
                "characterId": character_id,
                "messageCode": message_code,
                "messageName": message_name,
                "data": kwargs,
            }
        )

    async def periodic_saving(self):
        while True:
            token_usage = llm_selector.get_token_usage()
            save_token_consumption_to_db(token_usage)
            await asyncio.sleep(1800)

    async def run(self):
        # Periodic Saving Task
        if self.config.get("save_trigger"):
            asyncio.create_task(self.periodic_saving())

        # Heartbeat Monitor
        if self.config.get("monitor_trigger"):
            await self.character_manager.start_monitoring()

        # HTTP Monitor
        if self.config.get("dashboard_trigger"):
            http_host = self.config.get("http_monitor_host")
            http_port = self.config.get("http_monitor_port")
            await self.web_monitor.setup(host=http_host, port=http_port)
            logger.info(f"🌐 HTTP Monitor started at http://{http_host}:{http_port}")

        ws_host = self.config.get("websocket_host")
        ws_port = self.config.get("websocket_port")

        # SSL Configuration
        if self.config.get("ssl_trigger"):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(
                certfile=self.config.get("ssl_certfile"),
                keyfile=self.config.get("ssl_keyfile"),
            )
            server = await websockets.serve(
                self.handler, ws_host, ws_port, ssl=ssl_context
            )

            logger.warning(f"🔗 WebSocket server started at wss://{ws_host}:{ws_port}")
        else:
            server = await websockets.serve(self.handler, ws_host, ws_port)
            logger.warning(f"🔗 WebSocket server started at ws://{ws_host}:{ws_port}")

        await server.wait_closed()


def main():
    logger.add(
        "agent_instance.log",
        filter=lambda record: record["extra"].get("agent_instance") == True,
        format="{time} {level} {message}",
    )

    logger.add(
        "conversation_instance.log",
        filter=lambda record: record["extra"].get("conversation_instance") == True,
        format="{time} {level} {message}",
    )

    # environment = "production" if sys.platform.startswith("linux") else "development"
    environment = "test"
    config = ConfigLoader(environment)
    server = AI_WS_Server(config)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
