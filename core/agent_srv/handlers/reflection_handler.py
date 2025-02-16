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
        conversation = agent_api.request_sync(
            method="GET",
            endpoint="/conversation/",
            params={
                "characterId": state["userid"],
                "start_day": state["meta"]["day"] - 1,
            },
        )
        failed_actions = await format_queue_data(state["false_action_queue"])
        payload = {
            "daily_objectives": format_daily_obj(state["decision"]["daily_objective"]),
            "action_results": state["decision"]["action_result"],
            "failed_actions": failed_actions,
            "reflection_ar": state["prompts"]["reflection_ar"],
            "focus_topic": state["prompts"]["focus_topic"],
            "depth_of_reflection": state["prompts"]["depth_of_reflection"],
            "level_of_detail": state["prompts"]["level_of_detail"],
            "tone_and_style": state["prompts"]["tone_and_style"],
            "status_changes": format_status_changes(
                state["past_stats"],
                state["character_stats"],
                fields=[
                    "health",
                    "energy",
                    "hungry",
                    "education",
                    "education_experience",
                    "money",
                    "occupation",
                    "efficiency",
                    "inventory",
                ],
            ),
            "conversation_memory": format_conversation_data(
                state["userid"], conversation
            ),
        }
        daily_reflection = await self.api_retry(
            daily_reflection_generator,
            payload,
            state,
            Reflection,
        )

        full_prompt = daily_reflection_prompt.format(**payload)
        logger.info("======generate_daily_reflection======\n" + full_prompt)
        state["decision"]["reflection"].append(daily_reflection.reflection)
        save_reflection_to_db(
            state["userid"], {"new_reflection": daily_reflection.reflection}
        )
        response = await self.send_message(
            state,
            "daily_reflection",
            11,
            {
                "reflection": daily_reflection.reflection,
            },
        )
        if state.get("instance"):
            state["instance"].log_message("received", response)

        logger.info(f"🔍 DAILY_REFLECTION INVOKED with {daily_reflection.reflection}")

        return {"current_pointer": "Daily_Reflection"}

    async def generate_arc(self, state):
        character_arc_generator = self.create_planner(
            generate_character_arc_prompt,
            state.get("character_stats", {}).get("model_type"),
            CharacterArc,
            0.8,
        )

        character_info = game_api.request_sync(
            method="GET", endpoint=f"/characters/getById/{state['userid']}"
        )
        character_arc = await character_arc_generator.ainvoke(
            {
                "character_stats": format_character_data(state["character_stats"]),
                "character_info": character_info,
                "daily_objectives": format_daily_obj(
                    state["decision"]["daily_objective"]
                ),
                "daily_reflection": state["decision"]["reflection"],
                "action_results": state["decision"]["action_result"],
            }
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
