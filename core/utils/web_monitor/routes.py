from aiohttp import web
from datetime import datetime
from pathlib import Path
import logging
import asyncio
import os
import copy

logger = logging.getLogger(__name__)


class WebMonitor:
    def __init__(self, character_manager):
        self.character_manager = character_manager
        self.template_dir = Path(__file__).parent / "templates"

    async def index(self, request):
        with open(self.template_dir / "index.html") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html")

    async def user_messages(self, request):
        with open(self.template_dir / "user_messages.html") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html")

    async def get_status(self, request):
        try:
            character_status = await self.character_manager.get_status()

            status = {
                "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "character_monitor": character_status,
            }

            return web.json_response(status)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def get_user_messages(self, request):
        character_id = int(request.match_info["character_id"])
        character = self.character_manager.get_character(character_id)
        if not character:
            return web.json_response({"error": "Character not found"}, status=404)

        return web.json_response(character.agent_instance.message_log)

    async def get_user_state(self, request):
        character_id = int(request.match_info["character_id"])
        character = self.character_manager.get_character(character_id)
        if not character:
            return web.json_response({"error": "Character not found"}, status=404)

        try:
            state_data = {}
            original_state = character.agent_instance.state

            for key, value in original_state.items():
                if isinstance(value, (asyncio.Future, asyncio.Task)):
                    continue
                if isinstance(value, asyncio.Queue):
                    state_data[key] = list(value._queue)
                    continue
                if key in ["websocket", "instance"]:
                    continue
                if key == "decision":
                    state_data[key] = {}
                    for dk, dv in value.items():
                        if dk in ["expanded_meta_seq", "daily_objective"]:
                            state_data[key][dk] = list(dv)
                        else:
                            try:
                                state_data[key][dk] = copy.deepcopy(dv)
                            except:
                                logger.warning(f"Cannot copy decision.{dk}, skipping")
                    continue
                try:
                    state_data[key] = copy.deepcopy(value)
                except:
                    logger.warning(f"Error copying state for key {key}")
                    continue

            logger.info(f"Character {character_id} state: {state_data}")
            return web.json_response(state_data)
        except Exception as e:
            logger.error(f"Error retrieving state for character {character_id}: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_output_log(self, request):
        log_file = os.path.join("logs", "output.log")

        if not os.path.exists(log_file):
            return web.json_response({"error": "Log file not found"}, status=404)

        with open(log_file, "r") as f:
            log_content = f.read()

        return web.Response(text=log_content, content_type="text/plain")

    async def setup(self, host="localhost", port=8000):
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/status", self.get_status)
        app.router.add_get("/user/{character_id}", self.user_messages)
        app.router.add_get("/api/messages/{character_id}", self.get_user_messages)
        app.router.add_get("/api/state/{character_id}", self.get_user_state)
        app.router.add_get("/logs/output", self.get_output_log)

        app.router.add_static("/logs/", path="logs", name="logs")

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        return site
