from core.agent_srv.node_engines import create_planner
from utils import *
from node_model import *
from core.db.database_api_utils import make_api_request_sync
from core.db.game_api_utils import (
    make_api_request_async as make_api_request_async_backend,
    make_api_request_sync as make_api_request_sync_backend,
)
from core.agent_srv.prompts import trade_planner_prompt


async def generate_trading_objective(state: RunningState):
    obj_planner = create_planner(
        obj_planner_prompt,
        state.get("character_stats", {}).get("model_type"),
        DailyObjective,
        0.7,
    )
    dev_dict = make_api_request_sync("GET", f"/production_path/{state['userid']}").get(
        "data", {}
    )
    # print(dev_dict)
    state["meta"]["production_graph"] = format_level_graph(
        dev_dict,
        state["character_stats"]["inventory"],
        state["character_stats"]["energy"],
    )

    decision_response = make_api_request_sync(
        "GET", "/action_log/", params={"characterId": state["userid"], "count": 5}
    )
    last_decision = decision_response.get("data", {})
    retry_count = 0
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
        "past_reflection": last_decision.get("reflection", []) if last_decision else [],
        "production_graph": state["meta"]["production_graph"],
    }

    print(obj_planner_prompt.format(**payload))
    while retry_count < 3:
        try:
            planner_response = await obj_planner.ainvoke(payload)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_daily_objective: {e}"
            )
            retry_count += 1
            if retry_count == 3:
                raise Exception("Too many retries on generate_daily_objective")
            continue
    full_prompt = obj_planner_prompt.format(**payload)
    logger.info("======generate_daily_objective======\n" + full_prompt)
    state["decision"]["daily_objective"].append(planner_response.objectives)
    save_decision_to_db(
        state["userid"], {"objectives": planner_response.objectives}, "daily_objectives"
    )

    logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.progress}")
    logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.objectives}")

    return {"current_pointer": "objectives_planner"}
