from .base_handler import BaseHandler
from core.agent_srv.prompts import *
from core.agent_srv.node_model import Reflection, CharacterArc
from core.agent_srv.utils import *
from core.db.api_client import agent_api, game_api
from loguru import logger


class ReflectionHandler(BaseHandler):

    async def generate_reflection(self, state):
        daily_reflection_generator = self.create_planner(
            daily_reflection_prompt,
            state.get("character_stats", {}).get("model_type"),
            Reflection,
            0.8,
        )
        action_log = agent_api.request_sync(
            method="GET",
            endpoint="/action_log/",
            params={
                "characterId": state["userid"],
                "game_day": state["meta"]["day"] - 1,
            },
        )
        action_log_str = (
            "# Today's actions\n"
            + "".join(
                [
                    f"{action['command']}: {action['description']} (Execution result: {action['state']})\n"
                    for action in action_log["log"]
                ]
            )
            if action_log["log"]
            else ""
        )

        price_response = game_api.request_sync(
            method="GET", endpoint="/ammPool/getAveragePrice"
        )
        item_str = get_item_str(price_response)

        production_path_str = get_production_path_str()

        job_str = get_job_str()

        character_data_str = "# Character Info\n"+ get_character_data_str(
            characterId=state["userid"], character_data=state["character_stats"]
        )

        character_name = state["character_stats"].get("name", "None")

        industry_data=agent_api.request_sync(
            method="GET",
            endpoint=f"/industry/{state["userid"]}/goal"
        )
        payload = {
            "action_log_str": action_log_str,
            "item_str":item_str,
            "production_path_str":production_path_str,
            "job_str":job_str,
            "character_data_str":character_data_str,
            "character_name":character_name,
            "industry":industry_data['industry'],
            "goal":industry_data['goal'],
        }
        daily_reflection = await self.api_retry(
            daily_reflection_generator,
            payload,
            state,
            Reflection,
        )

        full_prompt = daily_reflection_prompt.format(**payload)
        logger.info("======generate_daily_reflection======\n" + full_prompt)
        reflection_summary = (
            f"Resource Management: {daily_reflection.resource_management}\n"
            f"Energy and Health: {daily_reflection.energy_and_health}\n"
            f"Time Efficiency: {daily_reflection.time_efficiency}\n"
            f"Financial Strategy: {daily_reflection.financial_strategy}\n"
            f"Task Prioritization: {daily_reflection.task_prioritization}"
        )
        state["decision"]["reflection"].append(reflection_summary)
        save_reflection_to_db(
            state["userid"], {"new_reflection": reflection_summary}
        )
        response = await self.send_message(
            state,
            "daily_reflection",
            11,
            {
                "reflection": reflection_summary,
            },
        )
        if state.get("instance"):
            state["instance"].log_message("received", response)

        logger.info(f"🔍 DAILY_REFLECTION INVOKED with {reflection_summary}")

        return {"current_pointer": "Daily_Reflection"}

    async def generate_arc(self, state):
        character_arc_generator = self.create_planner(
            generate_character_arc_prompt,
            state.get("character_stats", {}).get("model_type"),
            CharacterArc,
            0.8,
        )
        conversation_str = agent_api.request_sync(
            method="GET",
            endpoint="/conversation/str",
            params={"characterId":state["userid"], "start_day":state["meta"]["day"] - 1},
        )
        conversation_str = "# Today's conversations\n" + conversation_str if conversation_str else ""

        action_log = agent_api.request_sync(
            method="GET",
            endpoint="/action_log/",
            params={"characterId":state["userid"], "game_day":state["meta"]["day"] - 1},
        )
        action_log_str = "# Today's actions\n" + "".join([f"{action['command']}: {action['description']} (Execution result: {action['state']})\n" for action in action_log['log']]) if action_log['log'] else ""

        initial_character_arc=agent_api.request_sync(
            method="GET",
            endpoint="/character_arc/",
            params={"characterId":state["userid"], "k":1},
        )
        initial_character_arc_str = (f"# Character Initial Setup\n" if initial_character_arc else "") + ''.join([f"\nbelief: {character['belief']}\nmood: {character['mood']}\nvalues: {character['values']}\nhabits: {character['habits']}\npersonality: {character['personality']}\n" for character in initial_character_arc])

        character_name = state["character_stats"].get("name", "None")
        biography = state["character_stats"].get("biography", "None")

        payload = {
            "conversation_str": conversation_str,
            "action_log_str": action_log_str,
            "initial_character_arc_str": initial_character_arc_str,
            "character_name": character_name,
            "biography": biography,
        }
        full_prompt = generate_character_arc_prompt.format(**payload)
        logger.info("======generate_character_arc======\n" + full_prompt)
        character_arc = await self.api_retry(
            character_arc_generator,
            payload,
            state,
            CharacterArc,
        )
        character_arc_data = {
            "characterId": state["userid"],
            **dict(character_arc),
        }
        response = await self.send_message(
            state,
            "character_arc",
            12,
            {"character_arc": character_arc_data},
        )
        if state.get("instance"):
            state["instance"].log_message("received", response)
        logger.info(f"📜 Character Arc: {character_arc_data}")
        agent_api.request_sync(
            method="POST", endpoint="/character_arc/", data=character_arc_data
        )

        return {"current_pointer": "Character_Arc"}
