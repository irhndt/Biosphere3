from .base_handler import BaseHandler
from core.agent_srv.prompts import *
from core.agent_srv.action_simulator import ActionSimulator
from loguru import logger
from core.agent_srv.node_model import *
from core.db.api_client import game_api, agent_api
from core.agent_srv.utils import *
import traceback


class PlanningHandler(BaseHandler):
    async def generate_daily_objective(self, state: RunningState):
        obj_planner = self.create_planner(
            obj_planner_prompt,
            state.get("character_stats", {}).get("model_type"),
            DailyObjective,
            0.7,
        )
        dev_dict = agent_api.request_sync(
            method="GET", endpoint=f"/production_path/{state['userid']}"
        )
        state["meta"]["production_graph"] = format_level_graph(
            dev_dict,
            state["character_stats"]["inventory"],
            state["character_stats"]["energy"],
        )

        last_decision = agent_api.request_sync(
            method="GET",
            endpoint="/action_log/",
            params={"characterId": state["userid"], "count": 5},
        )
        daily_objectives_list = list(state["decision"]["daily_objective"])
        if len(daily_objectives_list) > 0:
            daily_objectives_list = daily_objectives_list[-1]
        payload = {
            "character_stats": format_character_data(
                state["character_stats"],
                fields=["money", "inventory"],
            ),
            "past_objectives": format_daily_obj(daily_objectives_list),
            "life_style": state["prompts"]["life_style"],
            "past_reflection": (
                last_decision.get("reflection", []) if last_decision else []
            ),
            "production_graph": state["meta"]["production_graph"],
        }

        print(obj_planner_prompt.format(**payload))
        planner_response = await self.api_retry(
            obj_planner.ainvoke,
            payload,
            state,
            DailyObjective,
        )
        full_prompt = obj_planner_prompt.format(**payload)
        logger.info("======generate_daily_objective======\n" + full_prompt)
        state["decision"]["daily_objective"].append(planner_response.objectives)
        save_decision_to_db(
            state["userid"],
            {"objectives": planner_response.objectives},
            "daily_objectives",
        )

        logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.progress}")
        logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.objectives}")

        return {"current_pointer": "objectives_planner"}

    async def generate_crafting_and_trading_sequence(self, state):
        """生成制作交易序列"""
        crafting_and_trading_planner = self.create_planner(
            crafting_and_trading_prompt,
            state.get("character_stats", {}).get("model_type"),
            DetailedMetaActionSequence,
            0.3,
        )

        payload = {
            "character_stats": format_character_data(
                state["character_stats"],
                fields=[
                    "money",
                    "energy",
                    "health",
                    "hungry",
                    "education",
                    "education_experience",
                    "occupation",
                    "effciency",
                    "inventory",
                ],
            ),
            "market_data": format_market(state["public_data"]["market_data"]),
            "daily_objectives": (
                state["decision"]["daily_objective"][-1]
                if state["decision"]["daily_objective"]
                else []
            ),
            "production_graph": state["meta"]["production_graph"],
            "example_output": meta_seq_example_out,
            "forbidden_example_output": meta_seq_forbidden_example_out,
        }
        print(crafting_and_trading_prompt.format(**payload))
        crafting_and_trading_sequence = await self.api_retry(
            crafting_and_trading_planner.ainvoke,
            payload,
            state,
            DetailedMetaActionSequence,
        )
        state["decision"]["detailed_meta_seq"] = []
        for craft_and_trade in crafting_and_trading_sequence.action_sequence:
            state["decision"]["detailed_meta_seq"].append(craft_and_trade.model_dump())

        state["decision"]["meta_seq"] = [
            action.action for action in crafting_and_trading_sequence.action_sequence
        ]
        try:
            simulate_list = ActionSimulator().simulate(
                state["decision"]["meta_seq"],
                state["character_stats"],
                get_amm_data_from_db(),
            )
        except Exception as e:
            logger.warning("ActionSimulator Failed, use the original sequence")
            print(traceback.format_exc())
            simulate_list = state["decision"]["meta_seq"]
        for item in simulate_list:
            state["decision"]["expanded_meta_seq"].append(item)
        logger.info(
            f"🔨 User {state['userid']}: CRAFTING_AND_TRADING_SEQUENCE INVOKED with {state['decision']['meta_seq']}"
        )

        logger.info(
            f"🔨 User {state['userid']}: CRAFTING_AND_TRADING_SEQUENCE EXPANDED with {state['decision']['expanded_meta_seq']}"
        )

        await self.generate_emoji_sequence(state, simulate_list)
        return {"current_pointer": "meta_action_sequence"}

    async def replan_meta_action(self, state):
        meta_action_replanner = self.create_planner(
            replanner_prompt,
            state.get("character_stats", {}).get("model_type"),
            DetailedMetaActionSequence,
            0.3,
        )
        false_action_info = state["false_action_queue"].get_nowait()

        logger.warning(
            f"⚠️ User {state['userid']}: Replanning failed action: {false_action_info}"
        )

        logger.warning(
            f"⚠️ User {state['userid']}: Failed Plan list waiting to be planned: {format_detailed_meta_seq(state['decision']['detailed_meta_seq'], false_action_info['actionName'])}"
        )
        payload = {
            "character_stats": format_character_data(
                state["character_stats"],
                fields=[
                    "money",
                    "energy",
                    "health",
                    "hungry",
                    "education",
                    "education_experience",
                    "occupation",
                    "effciency",
                    "inventory",
                ],
            ),
            "market_data": format_market(state["public_data"]["market_data"]),
            "current_action_list": format_meta_seq(
                list(state["decision"]["expanded_meta_seq"])
            ),
            "fail_action_info": format_false_action_info(false_action_info),
        }
        meta_action_sequence = await self.api_retry(
            meta_action_replanner.ainvoke,
            payload,
            state,
            DetailedMetaActionSequence,
        )

        meta_seq_list = []
        for item in meta_action_sequence.action_sequence:
            meta_seq_list.append(item.action)

        state["decision"]["meta_seq"] = meta_seq_list
        try:
            simulate_list = ActionSimulator().simulate(
                state["decision"]["meta_seq"],
                state["character_stats"],
                get_amm_data_from_db(),
            )
        except Exception as e:
            logger.warning("ActionSimulator Failed, use the original sequence")
            print(traceback.format_exc())
            simulate_list = state["decision"]["meta_seq"]

        for item in simulate_list:
            state["decision"]["expanded_meta_seq"].append(item)
        detailed_meta_seq = []
        for item in meta_action_sequence.action_sequence:
            detailed_meta_seq.append(item.model_dump())

        # pprint(detailed_meta_seq)
        state["decision"]["detailed_meta_seq"] = detailed_meta_seq

        await self.generate_emoji_sequence(state, simulate_list)

        return {"current_pointer": "Replan_Meta_Action"}

    async def generate_emoji_sequence(self, state, action_list):
        emoji_seq_generator = self.create_planner(
            generate_emoji_sequence_prompt,
            state.get("character_stats", {}).get("model_type"),
            EmojiSequence,
            0.8,
        )

        squence_format = """{"response": [{"content": "I hate work overtime!", "emoji": "🥺😭"}, {"content": "So tired, but got lots of fishes", "emoji": "🐟😆"}]}"""

        # Split the action list into 10 actions each

        emojis = []
        descriptions = []
        for i in range(0, len(action_list), 10):
            pay_load = {
                "personality": state["character_stats"]["personality"],
                "action_list": refine_list(action_list[i : i + 10]),
                "sequence_format": squence_format,
            }
            emoji_sequence_sep = await self.api_retry(
                emoji_seq_generator.ainvoke,
                pay_load,
                state,
                EmojiSequence,
            )
            emojis.extend([desc.emoji for desc in emoji_sequence_sep.response])
            descriptions.extend([desc.content for desc in emoji_sequence_sep.response])

        logger.info(f"📜 User {state['userid']}: EMOJI_SEQUENCE INVOKED with {emojis}")
        logger.info(
            f"📜 User {state['userid']}: EMOJI_SEQUENCE INVOKED with {descriptions}"
        )

        response = await self.send_message(
            state,
            "actionList",
            6,
            {
                "command": action_list,
                "emoji": emojis,
                "description": descriptions,
            },
        )
        if state.get("instance"):
            state["instance"].log_message("received", response)
