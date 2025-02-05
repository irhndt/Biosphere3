from core.agent_srv.node_engines import create_planner
from core.agent_srv.utils import *
from core.agent_srv.node_model import *
from core.agent_srv.prompts import trade_planner_prompt, merger_prompt
from core.db.api_client import game_api, agent_api


async def generate_trading_objective(state: RunningState):
    obj_planner = create_planner(
        trade_planner_prompt,
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
        "past_reflection": last_decision.get("reflection", []) if last_decision else [],
        "production_graph": state["meta"]["production_graph"],
    }

    print(trade_planner_prompt.format(**payload))
    while retry_count < 3:
        try:
            planner_response = await obj_planner.ainvoke(payload)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_daily_objective: {e}"
            )
            # logger.error(e.doc)
            retry_count += 1
            if retry_count == 3:
                raise Exception("Too many retries on generate_daily_objective")
            continue
    full_prompt = trade_planner_prompt.format(**payload)
    logger.info("======generate_daily_objective======\n" + full_prompt)
    state["decision"]["trade_objective"].append(planner_response.objectives)
    # save_decision_to_db(
    #     state["userid"], {"objectives": planner_response.objectives}, "daily_objectives"
    # )

    logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.progress}")
    logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.objectives}")

    return {"current_pointer": "objectives_planner"}


async def merge_objectives(state: RunningState):
    # merge objectives
    merger = create_planner(
        merger_prompt,
        state.get("character_stats", {}).get("model_type"),
        DailyObjective,
        0.7,
    )
    daily_objectives_list = list(state["decision"]["daily_objective"])
    last_daily_objective = daily_objectives_list[-1]  # MUST HAVE AT LEAST 1 OBJECTIVE
    last_trade_objective = state["decision"]["trade_objective"]
    payload = {
        "current_daily_objectives": format_daily_obj(last_daily_objective),
        "past_daily_objectives": format_daily_obj(
            daily_objectives_list[-2] if len(daily_objectives_list) > 1 else []
        ),
        "current_trading_objectives": format_daily_obj(last_trade_objective),
        "additional_info": state.get("decision", {}).get("additional_info", ""),
    }

    print(merger_prompt.format(**payload))
    merger_response = await merger.ainvoke(payload)

    full_prompt = merger_prompt.format(**payload)

    logger.info("======merge_objectives======\n" + full_prompt)
    # state["decision"]["daily_objective"] = merger_response.objectives
    logger.info(
        f"🌞 MERGER INVOKED with {merger_response.progress}\n"
        f" and\n {merger_response.objectives}"
    )


async def main():
    import asyncio
    from core.agent_srv.node_engines import generate_daily_objective

    state = await get_initial_state_from_db(432543, "websocket")
    logger.info(f"🚀 User {state['userid']} starting node engines")

    # Run generate_trading_objective and generate_daily_objective concurrently
    await asyncio.gather(
        generate_trading_objective(state),
        generate_daily_objective(state),
    )

    # Then run merge_objectives
    await merge_objectives(state)


if __name__ == "__main__":
    asyncio.run(main())
