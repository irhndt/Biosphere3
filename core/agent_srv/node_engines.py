import json
from loguru import logger
import sys
from pprint import pprint

sys.path.append(".")

from core.agent_srv.node_model import (
    DailyObjective,
    MetaActionSequence,
    CV,
    MayorDecision,
    RunningState,
    CharacterArc,
    Reflection,
    AccommodationDecision,
    DetailedMetaActionSequence,
    RefinedMetaActionSequence,
    EmojiSequence,
)
from core.agent_srv.prompts import *
from core.agent_srv.action_simulator import ActionSimulator
from core.utils.llm_factory import llm_selector
from core.db.database_api_utils import make_api_request_sync
from core.db.game_api_utils import (
    make_api_request_async as make_api_request_async_backend,
    make_api_request_sync as make_api_request_sync_backend,
)
from core.agent_srv.utils import (
    format_dict,
    save_decision_to_db,
    format_role_actions,
    format_market,
    format_character_data,
    format_conversation_data,
    format_queue_data,
    format_trade_and_craft_sequence,
    format_level_graph,
    format_daily_obj,
    get_character_data_async,
    get_prompt_data_from_db,
    get_market_data_from_db,
    format_status_changes,
    format_false_action_info,
    format_detailed_meta_seq,
    format_meta_seq,
)


def create_planner(prompt_template, model_name, output_type, temperature=0.5):
    return prompt_template | llm_selector.get_llm(
        model_name=model_name, temperature=temperature
    ).with_structured_output(output_type)


async def generate_daily_objective(state: RunningState):
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
    payload = {
        "character_stats": format_character_data(
            state["character_stats"],
            fields=["money", "inventory"],
        ),
        "past_objectives": format_daily_obj(state["decision"]["daily_objective"]),
        "life_style": state["prompts"]["life_style"],
        "past_reflection": last_decision.get("reflection", []) if last_decision else [],
        "production_graph": state["meta"]["production_graph"],
    }
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
        state["userid"],
        {"daily_objectives": planner_response.objectives},
        "daily_objectives",
    )

    logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.progress}")
    logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.objectives}")

    return {"current_pointer": "objectives_planner"}


async def generate_crafting_and_trading_sequence(state: RunningState):
    crafting_and_trading_planner = create_planner(
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
    # print(crafting_and_trading_prompt.format(**payload))
    retry_count = 0
    while retry_count < 3:
        try:
            crafting_and_trading_sequence = await crafting_and_trading_planner.ainvoke(
                payload
            )
            # print("crafting_and_trading_sequence: \n", crafting_and_trading_sequence)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_crafting_and_trading_sequence: {e}"
            )
            retry_count += 1
            if retry_count == 3:
                raise Exception(
                    "Too many retries on generate_crafting_and_trading_sequence"
                )
            continue

    state["decision"]["detailed_meta_seq"] = []
    for craft_and_trade in crafting_and_trading_sequence.action_sequence:
        state["decision"]["detailed_meta_seq"].append(craft_and_trade.model_dump())

    # pprint.pprint(
    #     state["decision"]["detailed_meta_seq"],
    # )

    state["decision"]["meta_seq"] = [
        action.action for action in crafting_and_trading_sequence.action_sequence
    ]
    state["decision"]["expanded_meta_seq"] = ActionSimulator().simulate(
        state["decision"]["meta_seq"],
        state["character_stats"],
        state["public_data"]["market_data"],
    )
    logger.info(
        f"🔨 CRAFTING_AND_TRADING_SEQUENCE INVOKED with {state['decision']['meta_seq']}"
    )

    logger.info(
        f"🔨 CRAFTING_AND_TRADING_SEQUENCE EXPANDED with {state['decision']['expanded_meta_seq']}"
    )

    emoji_seq_generator = create_planner(
        generate_emoji_sequence_prompt,
        state.get("character_stats", {}).get("model_type"),
        EmojiSequence,
        0.8,
    )

    squence_format = """{"response": [{"content": "I hate work overtime!", "emoji": "🥺😭"}, {"content": "So tired, but got lots of fishes", "emoji": "🐟😆"}]}"""

    pay_load = {
        "personality": state["character_stats"]["personality"],
        "action_list": state["decision"]["expanded_meta_seq"],
        "sequence_format": squence_format,
    }
    retry_count = 0
    while retry_count < 3:
        try:
            emoji_sequence = await emoji_seq_generator.ainvoke(pay_load)
            if emoji_sequence.response:
                break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_emoji_sequence: {e}"
            )
            retry_count += 1
            if retry_count == 3:
                raise Exception(
                    "Too many retries on generate_crafting_and_trading_sequence"
                )
            continue

    for emoji_and_description in emoji_sequence.response:
        state["decision"]["action_description"].append(emoji_and_description.content)

    # meta_action_sequence = [
    #     action.action for action in crafting_and_trading_sequence.action_sequence
    # ]
    meta_action_sequence = state["decision"]["expanded_meta_seq"]
    # save_decision_to_db(
    #     state["userid"],
    #     {
    #         "meta_seq": meta_action_sequence,
    #         "action_description": state["decision"]["action_description"],
    #     },
    # )

    response = await send_message(
        state,
        "actionList",
        6,
        {
            "command": meta_action_sequence,
            "emoji": [desc.emoji for desc in emoji_sequence.response],
            "description": state["decision"]["action_description"],
        },
    )
    logger.info(f"🧠 META_ACTION_SEQUENCE INVOKED with {meta_action_sequence}")
    pprint(
        {
            "command": meta_action_sequence,
            "emoji": [desc.emoji for desc in emoji_sequence.response],
            "description": state["decision"]["action_description"],
        },
    )
    if state.get("instance"):
        state["instance"].log_message("received", json.dumps(response))
    # state["instance"].log_message("received", json.dumps(response))

    return {"current_pointer": "meta_action_sequence"}


async def generate_meta_action_sequence(state: RunningState):
    meta_action_sequence_planner = create_planner(
        meta_action_sequence_prompt,
        state.get("character_stats", {}).get("model_type"),
        MetaActionSequence,
        0.3,
    )
    payload = {
        "daily_objective": (
            state["decision"]["daily_objective"][-1]
            if state["decision"]["daily_objective"]
            else []
        ),
        "tool_functions": state["meta"]["tool_functions"],
        "locations": state["meta"]["available_locations"],
        "inventory": state["character_stats"]["inventory"],
        "market_data": state["public_data"]["market_data"],
        "task_priority": state["prompts"]["task_priority"],
        "max_actions": state["prompts"]["max_actions"],
        "additional_requirements": state["prompts"]["meta_seq_ar"],
    }

    retry_count = 0
    while retry_count < 3:
        try:
            meta_action_sequence = await meta_action_sequence_planner.ainvoke(payload)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_daily_objective: {e}"
            )
            retry_count += 1
            if retry_count == 3:
                raise Exception("Too many retries on generate_meta_action_sequence")
            continue

    # full_prompt = meta_action_sequence_prompt.format(**payload)
    # logger.info("======generate_meta_action_sequence======\n" + full_prompt)
    for item in meta_action_sequence.meta_action_sequence:
        state["decision"]["meta_seq"].append(item)
    for item in meta_action_sequence.description_sequence:
        state["decision"]["action_description"].append(item)
    # save_decision_to_db(
    #     state["userid"],
    #     {
    #         "meta_seq": meta_action_sequence.meta_action_sequence,
    #         "action_description": meta_action_sequence.description_sequence,
    #     },
    # )

    response = await send_message(
        state,
        "actionList",
        6,
        {
            "command": meta_action_sequence.meta_action_sequence,
            "action_emoji": meta_action_sequence.action_emoji_sequence,
            "state_emoji": meta_action_sequence.state_emoji_sequence,
            "description": meta_action_sequence.description_sequence,
        },
    )
    state["instance"].log_message("received", json.dumps(response))
    logger.info(
        f"🧠 META_ACTION_SEQUENCE INVOKED with {meta_action_sequence.meta_action_sequence}"
    )

    return {"current_pointer": "meta_action_sequence"}


async def sensing_environment(state: RunningState):
    # update the latest state from db
    character_data = await get_character_data_async(state["userid"])
    prompt_data = await get_prompt_data_from_db(state["userid"])
    market_data = get_market_data_from_db()
    state["character_stats"] = character_data
    state["prompts"] = prompt_data
    state["public_data"]["market_data"] = market_data

    return {"current_pointer": "Sensing_Route"}


async def replan_action(state: RunningState):
    meta_seq_adjuster = create_planner(
        meta_seq_adjuster_prompt,
        state.get("character_stats", {}).get("model_type"),
        MetaActionSequence,
        0.3,
    )
    false_action = state["false_action_queue"].get_nowait()
    failed_action = false_action.get("actionName")
    error_message = false_action.get("msg")

    logger.info(f"🔄 User {state['userid']}: Replanning failed action: {failed_action}")

    # Analyze error type and context
    error_context = {
        "failed_action": failed_action,
        "error_message": error_message,
        "current_meta_seq": state["decision"]["meta_seq"][-1],
        "daily_objective": (
            state["decision"]["daily_objective"][-1]
            if state["decision"]["daily_objective"]
            else []
        ),
    }
    logger.info(f"🔧 User {state['userid']}: Error context: {error_context}")
    # try:
    # Generate new meta sequence with error context
    retry_count = 0
    while retry_count < 3:
        try:
            meta_action_sequence = await meta_seq_adjuster.ainvoke(
                {
                    "meta_seq": state["decision"]["meta_seq"][-1],
                    "tool_functions": state["meta"]["tool_functions"],
                    "locations": state["meta"]["available_locations"],
                    "failed_action": failed_action,
                    "error_message": error_message,
                    "replan_time_limit": state["prompts"]["replan_time_limit"],
                    "additional_requirements": state["prompts"]["meta_seq_adjuster_ar"],
                }
            )
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_daily_objective: {e}"
            )
            retry_count += 1
            if retry_count == 3:
                raise Exception("Too many retries on replan_action")
            continue

    logger.info(
        f"✨ User {state['userid']}: Generated new action sequence: {meta_action_sequence.meta_action_sequence}"
    )
    for item in meta_action_sequence.meta_action_sequence:
        state["decision"]["new_plan"].append(item)
    for item in meta_action_sequence.description_sequence:
        state["decision"]["action_description"].append(item)
    # save_decision_to_db(
    #     state["userid"],
    #     {
    #         "new_plan": meta_action_sequence.meta_action_sequence,
    #         "action_description": meta_action_sequence.description_sequence,
    #     },
    # )

    # Send new action sequence to client
    response = await send_message(
        state,
        "actionList",
        6,
        {
            "command": meta_action_sequence.meta_action_sequence,
            "action_emoji": meta_action_sequence.action_emoji_sequence,
            "state_emoji": meta_action_sequence.state_emoji_sequence,
            "description": meta_action_sequence.description_sequence,
        },
    )
    state["instance"].log_message("received", json.dumps(response))

    return {"current_pointer": "Replan_Action"}


async def generate_change_job_cv(instance, msg: dict):
    cv_generator = create_planner(generate_cv_prompt, "gpt-4o-mini", CV, 0.5)
    available_public_jobs = make_api_request_sync_backend(
        "GET", "/publicWork/getAll"
    ).get("data", [])

    user_id = msg.get("characterId")
    msg_data = msg.get("data", {})
    health = msg_data.get("health", 0)
    studyXp = msg_data.get("studyXp", 0)
    education = msg_data.get("education", "None")
    week = msg_data.get("week", 0)
    date = msg_data.get("date", 0)

    payload = {
        "available_public_jobs": available_public_jobs,
        "health": health,
        "experience": studyXp,
        "education": education,
    }
    cv = await cv_generator.ainvoke(payload)

    logger.info(f"📃 CV: {cv}")

    job_detail = make_api_request_sync_backend(
        "GET", f"/publicWork/getById/{cv.job_id}"
    )
    job_name = job_detail.get("data", {}).get("jobName", "")
    cv_request = {
        "jobid": cv.job_id,
        "characterId": user_id,
        "CV_content": cv.cv,
        "week": week,
        "health": health,
        "studyxp": studyXp,
        "date": date,
        "jobName": job_name,
        "election_status": "not_yet",
    }
    make_api_request_sync("POST", "/cv/", data=cv_request)

    mayor_decision = await generate_mayor_decision(
        cv, user_id, studyXp, education, date
    )
    if instance:
        response = await instance.send_message(
            {
                "characterId": user_id,
                "messageName": "mayor_decision",
                "messageCode": 10,
                "data": {"jobId": cv.job_id, "cv": cv.cv, **mayor_decision},
            }
        )
        instance.log_message("received", json.dumps(response))


async def generate_mayor_decision(
    cv: CV, user_id: int, experience: int, education: str, week: int = 0
):
    mayor_decision_generator = create_planner(
        mayor_decision_prompt, "gpt-4o-mini", MayorDecision, 0.7
    )
    public_work_info = make_api_request_sync_backend(
        "GET", f"/publicWork/getById/{cv.job_id}"
    ).get("data", {})

    check_result = make_api_request_sync_backend(
        "POST",
        "/publicWork/checkWork",
        data={
            "characterId": user_id,
            "newJobId": cv.job_id,
            "experience": experience,
            "education": education,
        },
    )
    code = check_result.get("code", 0)
    message = check_result.get("message", "")
    payload = {
        "cv": cv.cv,
        "public_work_info": public_work_info,
        "meet_requirements": {"meet": code == 1, "message": message},
    }
    mayor_decision = await mayor_decision_generator.ainvoke(payload)
    logger.info(f"🧔 Mayor decision: {mayor_decision.decision}")
    logger.info(f"🧔 Mayor comments: {mayor_decision.comments}")

    make_api_request_sync(
        "PUT",
        "/cv/election_status",
        data={
            "characterId": user_id,
            "jobid": cv.job_id,
            "week": week,
            "election_status": (
                "succeeded" if mayor_decision.decision == "yes" else "failed"
            ),
        },
    )

    return {
        "mayor_decision": mayor_decision.decision,
        "mayor_comments": mayor_decision.comments,
    }


async def generate_daily_reflection(state: RunningState):
    daily_reflection_generator = create_planner(
        daily_reflection_prompt,
        state.get("character_stats", {}).get("model_type"),
        Reflection,
        0.8,
    )
    conversation = make_api_request_sync(
        "GET",
        "/conversation/",
        params={"characterId": state["userid"], "start_day": state["meta"]["day"] - 1},
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
            state["userid"], conversation.get("data", [])
        ),
    }
    daily_reflection = await daily_reflection_generator.ainvoke(payload)

    full_prompt = daily_reflection_prompt.format(**payload)
    logger.info("======generate_daily_reflection======\n" + full_prompt)
    state["decision"]["reflection"].append(daily_reflection.reflection)
    save_decision_to_db(
        state["userid"], {"reflection": daily_reflection.reflection}, "reflection"
    )
    response = await send_message(
        state,
        "daily_reflection",
        11,
        {
            "reflection": daily_reflection.reflection,
        },
    )
    state["instance"].log_message("received", json.dumps(response))

    logger.info(f"🔍 DAILY_REFLECTION INVOKED with {daily_reflection.reflection}")

    return {"current_pointer": "Daily_Reflection"}


async def generate_character_arc(state: RunningState):
    character_arc_generator = create_planner(
        generate_character_arc_prompt,
        state.get("character_stats", {}).get("model_type"),
        CharacterArc,
        0.8,
    )
    character_info_task = make_api_request_async_backend(
        "GET", f"/characters/getById/{state['userid']}"
    )
    character_info_response = await character_info_task
    character_info = character_info_response.get("data", {})
    character_arc = await character_arc_generator.ainvoke(
        {
            "character_stats": format_character_data(state["character_stats"]),
            "character_info": character_info,
            "daily_objectives": format_daily_obj(state["decision"]["daily_objective"]),
            "daily_reflection": state["decision"]["reflection"],
            "action_results": state["decision"]["action_result"],
        }
    )
    character_arc_data = {
        "characterId": state["userid"],
        **dict(character_arc),
    }
    response = await send_message(
        state,
        "character_arc",
        12,
        {"character_arc": character_arc_data},
    )
    state["instance"].log_message("received", json.dumps(response))
    logger.info(f"📜 Character Arc: {character_arc_data}")
    make_api_request_sync("POST", "/character_arc/", data=character_arc_data)

    return {"current_pointer": "Character_Arc"}


async def generate_accommodation_decision(state: RunningState):
    accommodation_decision_generator = create_planner(
        accommodation_decision_prompt,
        state.get("character_stats", {}).get("model_type"),
        AccommodationDecision,
        0.5,
    )
    current_accommodation_response = await make_api_request_async_backend(
        "GET", f"/characterDormitory/getByCharacterIdNew/{state['userid']}"
    )
    current_accommodation_data = current_accommodation_response.get("data", None)

    current_accommodation = {"id": 1, "type": "Shelter"}
    if current_accommodation_data:
        current_accommodation["id"] = current_accommodation_data.get("id", 1)
        current_accommodation["type"] = current_accommodation_data.get(
            "type", "Shelter"
        )

    financial_status = {"money": state["character_stats"].get("money", 0)}

    accommodations_response = await make_api_request_async_backend(
        "GET", "/dormitory/getAll"
    )
    available_accommodations_raw = accommodations_response.get("data", [])

    necessary_fields = [
        "id",
        "type",
        "weeklyRent",
        "energyRecovery",
        "maxEnergy",
        "maxHealth",
        "maxHungry",
    ]
    available_accommodations = [
        {key: accommodation[key] for key in necessary_fields}
        for accommodation in available_accommodations_raw
    ]

    for acc in available_accommodations:
        weekly_rent = acc["weeklyRent"]
        if weekly_rent == 0:
            acc["affordable_weeks"] = 12
        else:
            affordable_weeks = financial_status["money"] // weekly_rent
            affordable_weeks = min(affordable_weeks, 12)
            acc["affordable_weeks"] = int(affordable_weeks)

    failure_reasons = []

    max_retries = 5
    retries = 0

    while retries < max_retries:
        payload = {
            "character_stats": format_character_data(state["character_stats"]),
            "current_accommodation": current_accommodation,
            "available_accommodations": available_accommodations,
            "financial_status": financial_status,
            "failure_reasons": failure_reasons,
        }

        try:
            accommodation_decision = await accommodation_decision_generator.ainvoke(
                payload
            )
            print("accommodation_decision: ", accommodation_decision)
        except Exception as e:
            logger.error(f"Invoke LLM Failed: {e}")
            failure_reasons.append(
                f"Attempt {retries + 1}: LLM invocation failed with error: {e}"
            )
            retries += 1
            continue

        logger.info(f"🏠 Attempt {retries + 1}:")
        logger.info(f"🏠 Accommodation ID: {accommodation_decision.accommodation_id}")
        logger.info(f"🏠 Lease Weeks: {accommodation_decision.lease_weeks}")
        logger.info(f"🏠 Comments: {accommodation_decision.comments}")

        selected_accommodation = next(
            (
                acc
                for acc in available_accommodations
                if acc["id"] == accommodation_decision.accommodation_id
            ),
            None,
        )

        if not selected_accommodation:
            failure_message = (
                f"Attempt {retries + 1}: Selected accommodation ID {accommodation_decision.accommodation_id} "
                f"does not exist. Please choose a valid accommodation."
            )

            failure_reasons.append(failure_message)
            logger.warning(f"🏠 {failure_message}")
            retries += 1
            continue

        lease_weeks = accommodation_decision.lease_weeks

        if not (1 <= lease_weeks <= 12):
            failure_message = (
                f"Attempt {retries + 1}: Lease weeks {lease_weeks} is out of allowed range (1-12). "
                f"Please choose a valid number of weeks."
            )

            failure_reasons.append(failure_message)
            logger.warning(f"🏠 {failure_message}")
            retries += 1
            continue

        weekly_rent = selected_accommodation["weeklyRent"]
        total_rent = weekly_rent * lease_weeks

        if total_rent > financial_status["money"]:
            failure_message = (
                f"Attempt {retries + 1}: Cannot afford total rent of {total_rent} for accommodation ID "
                f"{accommodation_decision.accommodation_id} over {lease_weeks} weeks. "
                f"Available money: {financial_status['money']}."
            )

            failure_reasons.append(failure_message)
            logger.warning(f"🏠 {failure_message}")
            retries += 1
            continue
        else:
            rent_data = {
                "characterId": state["userid"],
                "money": financial_status["money"],
                "dormitoryId": accommodation_decision.accommodation_id,
                "leaseWeeks": lease_weeks,
            }
            print("rent_data: ", rent_data)
            logger.info(f"🏠 Successfully rented accommodation.")
            break

    else:
        logger.error(
            f"🏠 Could not find an affordable accommodation after {max_retries} attempts."
        )
        return {
            "decision": {
                "accommodation_id": None,
                "lease_weeks": None,
                "accommodation_comments": "Could not find an affordable accommodation.",
            }
        }

    response = await send_message(
        state,
        "accommodationChange",
        8,
        {
            "accommodationId": accommodation_decision.accommodation_id,
            "leaseWeeks": lease_weeks,
            "comments": accommodation_decision.comments,
        },
    )
    state["instance"].log_message("received", json.dumps(response))

    return {"current_pointer": "Accommodation_Decision"}


async def send_message(state, message_name, message_code, data):
    if not state.get("instance"):
        logger.warning(f"⚠️ User {state['userid']}: Instance not found.")
        return
    response = {
        "characterId": state["userid"],
        "messageName": message_name,
        "messageCode": message_code,
        "data": data,
    }
    await state["instance"].send_message(response)
    return response


async def generate_emoji_seq(state):

    emoji_seq_generator = create_planner(
        generate_emoji_sequence_prompt,
        state.get("character_stats", {}).get("model_type"),
        EmojiSequence,
        0.8,
    )

    squence_format = """{"response": [{"content": "I hate work overtime!", "emoji": "🥺😭"}, {"content": "So tired, but got lots of fishes", "emoji": "🐟😆"}]}"""

    meta_seq = [action["action"] for action in state["decision"]["refined_meta_seq"]]

    pay_load = {
        "personality": state["character_stats"]["personality"],
        "action_list": meta_seq,
        "sequence_format": squence_format,
    }

    emoji_sequence = await emoji_seq_generator.ainvoke(pay_load)
    print("emoji_sequence: ", emoji_sequence)
    # return emoji_sequence


async def refine_meta_action_sequence(state: RunningState):
    meta_action_general_part_refiner = create_planner(
        meta_action_general_part_refiner_prompt,
        state.get("character_stats", {}).get("model_type"),
        RefinedMetaActionSequence,
        0.5,
    )

    example_out = """
[
    {
        "action": "action1",
        "cost": "25 energy total (5 energy per item × 5 items)",
        "expected_effect": "Get X <item> from crafting"
    },
    {
        "action": "action2",
        "cost": "None",
        "expected_effect": "Get X gold refund from selling"
    },
    {
        "action": "sleep 3,
        "cost": "None",
        "expected_effect": "Recover energy 30 (3x10) from sleeping"
    }
    {
        "action": "action3",
        "cost": "X gold",
        "expected_effect": ""
    },
    {
        "action": "goto school",
        "cost": "None",
        "expected_effect": "Get to school, ready to study"
    },
    ...
]
    """
    payload = {
        "daily_objectives": (
            state["decision"]["daily_objective"][-1]
            if state["decision"]["daily_objective"]
            else []
        ),
        "character_stats": format_character_data(
            state["character_stats"],
            fields=[
                "money",
                "energy",
                "health",
                "hunger",
                "education",
                "education_experience",
                "occupation",
                "effciency",
            ],
        ),
        "market_data": format_dict(state["public_data"]["market_data"]),
        "inventory": format_dict(state["character_stats"]["inventory"]),
        "current_trade_and_craft_sequence": format_trade_and_craft_sequence(
            state["decision"]["crafting_and_trading"]
        ),
        "example_output": example_out,
    }

    print(meta_action_general_part_refiner_prompt.format(**payload))

    retry_count = 0
    while retry_count < 3:
        try:
            meta_action_sequence = await meta_action_general_part_refiner.ainvoke(
                payload
            )
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_daily_objective: {e}"
            )
            retry_count += 1
            if retry_count == 3:
                raise Exception("Too many retries on refine_meta_action_sequence")
            continue

    print("meta_action_sequence: ", meta_action_sequence)

    meta_seq_list = []
    for item in meta_action_sequence.meta_action_sequence:
        meta_seq_list.append(item.model_dump())

    state["decision"]["refined_meta_seq"] = meta_seq_list


async def replan_meta_action_seq_new(state: RunningState):
    meta_action_replanner = create_planner(
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
        "current_action_list": format_meta_seq(state["decision"]["expanded_meta_seq"]),
        # if use detailed_meta_seq, please add:
        ## It includes the formatted list of actions the user has planned to take, as well as the reasons, effects and supposing status changes for each action.
        ## But it may contain errors or infeasible actions, waiting for your correction.
        "fail_action_info": format_false_action_info(false_action_info),
    }

    # print(replanner_prompt.format(**payload))
    retry_count = 0
    while retry_count < 3:
        try:
            meta_action_sequence = await meta_action_replanner.ainvoke(payload)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_daily_objective: {e}"
            )
            retry_count += 1
            if retry_count == 3:
                raise Exception("Too many retries on replan_meta_action_seq_new")
            continue

    meta_seq_list = []
    for item in meta_action_sequence.action_sequence:
        meta_seq_list.append(item.action)

    state["decision"]["meta_seq"] = meta_seq_list
    state["decision"]["expanded_meta_seq"] = ActionSimulator().simulate(
        state["decision"]["meta_seq"],
        state["character_stats"],
        state["public_data"]["market_data"],
    )
    detailed_meta_seq = []
    for item in meta_action_sequence.action_sequence:
        detailed_meta_seq.append(item.model_dump())

    # pprint(detailed_meta_seq)
    state["decision"]["detailed_meta_seq"] = detailed_meta_seq

    emoji_sequence_generator = create_planner(
        generate_emoji_sequence_prompt,
        state.get("character_stats", {}).get("model_type"),
        EmojiSequence,
        0.7,
    )

    squence_format = """{"response": [{"content": "I hate work overtime!", "emoji": "🥺😭"}, {"content": "So tired, but got lots of fishes", "emoji": "🐟😆"}]}"""

    pay_load = {
        "personality": state["character_stats"]["personality"],
        "action_list": state["decision"]["expanded_meta_seq"],
        "sequence_format": squence_format,
    }

    retry_count = 0
    while retry_count < 3:
        try:
            emoji_sequence = await emoji_sequence_generator.ainvoke(pay_load)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_emoji_sequence: {e}"
            )
            retry_count += 1
            if retry_count == 3:
                raise Exception("Too many retries on replan_meta_action_seq_new")
            continue

    for emoji_and_description in emoji_sequence.response:
        state["decision"]["action_description"].append(emoji_and_description.content)

    # save_decision_to_db(
    #     state["userid"],
    #     {
    #         "meta_seq": state["decision"]["expanded_meta_seq"],
    #         "action_description": state["decision"]["action_description"],
    #     },
    # )

    response = await send_message(
        state,
        "actionList",
        6,
        {
            "command": state["decision"]["expanded_meta_seq"],
            "emoji": [desc.emoji for desc in emoji_sequence.response],
            "description": state["decision"]["action_description"],
        },
    )
    state["instance"].log_message("received", json.dumps(response))

    return {"current_pointer": "Replan_Meta_Action"}


async def test_put_false_action_info(state: RunningState):
    false_action_info = {
        "actionName": "goto forest",
        "result": "No location named 'forest'.",
    }
    state["false_action_queue"].put_nowait(false_action_info)
    state["decision"]["detailed_meta_seq"] = [
        {
            "action": "goto forest",
            "cost": None,
            "inventory_after": None,
            "inventory_before": None,
            "reason": "Move to the forest to gather wood.",
            "status_after": None,
            "status_before": None,
        },
        {
            "action": "craft wood 10",
            "cost": "50 energy total (5 energy per item × 10)",
            "inventory_after": "Later inventory is {wood: 10}",
            "inventory_before": "Current inventory is {}",
            "reason": "Gather wood to prepare for crafting wooden_boards.",
            "status_after": "Later energy is 50/100",
            "status_before": "Current energy is 100/100",
        },
        {
            "action": "goto workshop",
            "cost": None,
            "inventory_after": None,
            "inventory_before": None,
            "reason": "Move to the workshop to craft wooden_boards.",
            "status_after": None,
            "status_before": None,
        },
        {
            "action": "craft wooden_board 3",
            "cost": "30 energy total (10 energy per item × 3)",
            "inventory_after": "Later inventory is {wood: 1, wooden_board: 3}",
            "inventory_before": "Current inventory is {wood: 10}",
            "reason": "Craft wooden_boards to prepare for book production.",
            "status_after": "Later energy is 20/100",
            "status_before": "Current energy is 50/100",
        },
        {
            "action": "goto home",
            "cost": None,
            "inventory_after": None,
            "inventory_before": None,
            "reason": "Go home to rest and recover energy.",
            "status_after": None,
            "status_before": None,
        },
        {
            "action": "sleep 8",
            "cost": "None",
            "inventory_after": None,
            "inventory_before": None,
            "reason": "The energy is too low, need to sleep to recover energy.",
            "status_after": "Later energy is 100/100",
            "status_before": "Current energy is 20/100",
        },
    ]
    return {"current_pointer": "Test_Put_False_Action_Info"}


if __name__ == "__main__":
    import asyncio
    import core.agent_srv.utils as utils

    # import pprint

    state = asyncio.run(utils.get_initial_state_from_db(432543, "websocket"))
    # pprint.pprint(state)
    logger.info(f"🚀 User {state['userid']} starting node engines")

    pprint(state["public_data"]["market_data"])
    # print(state)
    # TEST REPLAN ROUTINES
    # asyncio.run(test_put_false_action_info(state))
    # logger.success(f"🌞 User {state['userid']} finished putting false action info")

    # asyncio.run(replan_meta_action_seq_new(state))
    # logger.success(
    #     f"🌞 User {state['userid']} finished replanning meta action sequence"
    # )

    # pprint.pprint(state["decision"]["meta_seq"])

    # pprint(state["decision"]["detailed_meta_seq"])

    # # TEST PLANNING ROUTINES
    # asyncio.run(generate_daily_objective(state))
    # logger.success(f"🌞 User {state['userid']} finished daily objective")
    # asyncio.run(generate_crafting_and_trading_sequence(state))
    # logger.success(f"🌞 User {state['userid']} finished crafting and trading")
