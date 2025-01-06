import json
from loguru import logger

from core.agent_srv.node_model import (
    DailyObjective,
    MetaActionSequence,
    CV,
    MayorDecision,
    RunningState,
    CharacterArc,
    Reflection,
    AccommodationDecision,
)
from core.agent_srv.prompts import *
from core.llm_factory import LLMSelector
from core.db.database_api_utils import make_api_request_sync
from core.db.game_api_utils import (
    make_api_request_async as make_api_request_async_backend,
    make_api_request_sync as make_api_request_sync_backend,
)

llm_selector = LLMSelector()


def create_planner(prompt_template, model_name, output_type, temperature=0.5):
    return prompt_template | llm_selector.get_llm(
        model_name=model_name, temperature=temperature
    ).with_structured_output(output_type)


async def generate_daily_reflection(state: RunningState):
    daily_reflection_generator = create_planner(
        daily_reflection_prompt,
        state.get("character_stats", {}).get("model_type", "deepseek-chat"),
        Reflection,
        1,
    )
    payload = {
        "character_stats": format_character_data(state["character_stats"]),
        "daily_objectives": state["decision"]["daily_objective"],
        "failed_actions": str(state["false_action_queue"]),
        "additional_requirements": state["prompts"]["daily_reflection_ar"],
        "focus_topic": state["prompts"]["focus_topic"],
        "depth_of_reflection": state["prompts"]["depth_of_reflection"],
        "level_of_detail": state["prompts"]["level_of_detail"],
        "tone_and_style": state["prompts"]["tone_and_style"],
    }
    daily_reflection = await daily_reflection_generator.ainvoke(payload)

    full_prompt = daily_reflection_prompt.format(**payload)
    logger.info("======generate_daily_reflection======\n" + full_prompt)
    state["decision"]["daily_reflection"] = daily_reflection.reflection

    return {"decision": {"daily_reflection": daily_reflection.reflection}}


async def generate_daily_objective(state: RunningState):
    obj_planner = create_planner(
        obj_planner_prompt,
        state.get("character_stats", {}).get("model_type", "deepseek-chat"),
        DailyObjective,
        1.5,
    )
    response = make_api_request_sync_backend(
        "GET", f"/characters/getByIdS/{state['userid']}"
    )
    skill_list = response.get("data", {}).get("skillList", [])
    skill_name = [skill["skillName"] for skill in skill_list]
    try:
        with open("core/files/skill2actions.json", "r") as f:
            skills = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load skill actions: {e}")
    role_specific_actions = format_role_actions(skill_name, skills)
    state["meta"]["tool_functions"] += role_specific_actions

    retry_count = 0
    payload = {
        "character_stats": format_character_data(state["character_stats"]),
        "tool_functions": state["meta"]["tool_functions"],
        "locations": state["meta"]["available_locations"],
        # get the last 3 objectives
        "past_objectives": state.get("decision", []).get("daily_objective", [])[-3:],
        "daily_goal": state["prompts"]["daily_goal"],
        "refer_to_previous": state["prompts"]["refer_to_previous"],
        "market_data": state["public_data"]["market_data"],
        "life_style": state["prompts"]["life_style"],
        "additional_requirements": state["prompts"]["daily_objective_ar"],
    }
    while retry_count < 3:
        try:
            planner_response: RunningState = await obj_planner.ainvoke(payload)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in generate_daily_objective: {e}"
            )
            retry_count += 1
            continue
    full_prompt = obj_planner_prompt.format(**payload)
    logger.info("======generate_daily_objective======\n" + full_prompt)
    state["decision"]["daily_objective"].append(planner_response.objectives)

    logger.info(f"🌞 OBJ_PLANNER INVOKED with {planner_response.objectives}")
    return {"decision": {"daily_objective": [planner_response.objectives]}}


async def generate_meta_action_sequence(state: RunningState):
    meta_action_sequence_planner = create_planner(
        meta_action_sequence_prompt,
        state.get("character_stats", {}).get("model_type", "deepseek-chat"),
        MetaActionSequence,
        0,
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
            continue

    full_prompt = meta_action_sequence_prompt.format(**payload)
    logger.info("======generate_meta_action_sequence======\n" + full_prompt)
    state["decision"]["meta_seq"].append(meta_action_sequence.meta_action_sequence)

    await state["instance"].send_message(
        {
            "characterId": state["userid"],
            "messageName": "actionList",
            "messageCode": 6,
            "data": {
                "command": meta_action_sequence.meta_action_sequence,
                "action_emoji": meta_action_sequence.action_emoji_sequence,
                "state_emoji": meta_action_sequence.state_emoji_sequence,
                "description": meta_action_sequence.description_sequence,
            },
        }
    )
    logger.info(
        f"🧠 META_ACTION_SEQUENCE INVOKED with {meta_action_sequence.meta_action_sequence}"
    )
    return {"decision": {"meta_seq": meta_action_sequence.meta_action_sequence}}


async def sensing_environment(state: RunningState):
    token_usage = llm_selector.get_token_usage()
    print(token_usage)
    return {"current_pointer": "Process_Messages"}


async def replan_action(state: RunningState):
    meta_seq_adjuster = create_planner(
        meta_seq_adjuster_prompt,
        state.get("character_stats", {}).get("model_type", "deepseek-chat"),
        MetaActionSequence,
        0,
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
        "daily_objective": state["decision"]["daily_objective"][-1],
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
            continue

    logger.info(
        f"✨ User {state['userid']}: Generated new action sequence: {meta_action_sequence.meta_action_sequence}"
    )
    state["decision"]["new_plan"].append(meta_action_sequence.meta_action_sequence)

    # Send new action sequence to client
    await state["instance"].send_message(
        {
            "characterId": state["userid"],
            "messageName": "actionList",
            "messageCode": 6,
            "data": {
                "command": meta_action_sequence.meta_action_sequence,
                "action_emoji": meta_action_sequence.action_emoji_sequence,
                "state_emoji": meta_action_sequence.state_emoji_sequence,
                "description": meta_action_sequence.description_sequence,
            },
        }
    )

    return {"decision": {"meta_seq": meta_action_sequence.meta_action_sequence}}


async def generate_change_job_cv(instance, msg: dict):
    cv_generator = create_planner(generate_cv_prompt, "gpt-4o-mini", CV, 0.7)
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
        await instance.send_message(
            {
                "characterId": user_id,
                "messageName": "mayor_decision",
                "messageCode": 10,
                "data": {"jobId": cv.job_id, "cv": cv.cv, **mayor_decision},
            }
        )


async def generate_mayor_decision(
    cv: CV, user_id: int, experience: int, education: str, week: int = 0
):
    mayor_decision_generator = create_planner(
        mayor_decision_prompt, "gpt-4o-mini", MayorDecision, 0.5
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
            "election_status": mayor_decision.decision,
        },
    )

    return {
        "mayor_decision": mayor_decision.decision,
        "mayor_comments": mayor_decision.comments,
    }


async def generate_character_arc(state: RunningState):
    character_arc_generator = create_planner(
        generate_character_arc_prompt,
        state.get("character_stats", {}).get("model_type", "deepseek-chat"),
        CharacterArc,
        0.5,
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
            "daily_objectives": state["decision"]["daily_objective"],
            "daily_reflection": state["decision"].get("daily_reflection", ""),
            "action_results": state["decision"]["action_result"],
        }
    )
    character_arc_data = {
        "characterId": state["userid"],
        **dict(character_arc),
    }
    make_api_request_sync("POST", "/character_arc/", data=character_arc_data)
    state["decision"]["action_description"].append(dict(character_arc))
    return {"Character_Stats": {"character_arc": dict(character_arc)}}


def format_role_actions(roles, data):
    action_strings = ["Here are the actions you can perform based on your roles:"]

    for index, role in enumerate(roles, start=1):
        role_data = data.get(role, {})
        actions = role_data.get("actions", [])
        cost = role_data.get("cost", 0)
        materials = role_data.get("materials", {})

        # Format the actions
        action_str = f"{index}. craft [itemType:string] [num:int]: Craft a certain number of items and cost energy ({cost} per item)\n"
        action_str += "Constraints: Item must be in ItemType: ("
        action_str += ", ".join([action.split()[1] for action in actions])
        action_str += ") and you should have enough materials.\nHere's the rule:\n"

        # Format the materials
        for item, constraints in materials.items():
            if not constraints:
                action_str += f"- {item}: No materials required.\n"
            else:
                constraint_str = ", ".join(constraints)
                action_str += f"- {item}: Required materials: {constraint_str}\n"

        action_strings.append(action_str)

    return "\n".join(action_strings)


def format_character_data(character_data: dict) -> str:
    return (
        f"Health: {character_data.get('health', 'N/A')} - Represents the character's physical well-being.\n"
        f"Energy: {character_data.get('energy', 'N/A')} - Indicates how much energy the character has left.\n"
        f"Hungry: {character_data.get('hungry', 'N/A')} - Indicates the character's level of satiety; the higher, the fuller.\n"
        f"Education: {character_data.get('education', 'N/A')} - The level of education attained.\n"
        f"Education Experience: {character_data.get('education_experience', 'N/A')} - Experience points in education.\n"
        f"Money: {character_data.get('money', 'N/A')} - Current financial status.\n"
        f"Occupation: {character_data.get('occupation', 'N/A')} - Current job or role work at {character_data.get('work_place')}\n"
        f"Efficiency: {character_data.get('efficiency', 'N/A'):.2f} - Calculated efficiency based on various factors: "
        f"Efficiency = (Hungry Factor) * (Energy Factor) * (Health Factor) * (Wisdom Factor), where:\n"
        f"  - Hungry Factor = hungry / 100 if hungry < 50 else 1\n"
        f"  - Energy Factor = energy / 100\n"
        f"  - Health Factor = health / 100\n"
        f"  - Wisdom Factor = log(education_experience + 10, 10)\n"
        f"  Efficiency affects the crafting efficiency of items. If the efficiency is too low (lower than 0.2), "
        f"  it is advisable to improve the basic attributes first.\n"
        f"Inventory: {character_data.get('inventory', {})} - Items currently held by the character.\n"
        f"Personality: {character_data.get('personality', 'N/A')} - Describes the character's personality traits.\n"
        f"Long-term Goal: {character_data.get('long_term_goal', 'N/A')} - The character's long-term aspirations.\n"
        f"Short-term Goal: {character_data.get('short_term_goal', 'N/A')} - Immediate objectives.\n"
        f"Language Style: {character_data.get('language_style', 'N/A')} - Preferred communication style.\n"
        f"Biography: {character_data.get('biography', 'N/A')} - A brief background story.\n"
    )


async def generate_accommodation_decision(state: RunningState):
    accommodation_decision_generator = create_planner(
        accommodation_decision_prompt,
        state.get("character_stats", {}).get("model_type", "deepseek-chat"),
        AccommodationDecision,
        0.5,
    )
    # 1. 获取当前住宿信息
    current_accommodation_response = await make_api_request_async_backend(
        "GET", f"/dormitory/getById/{state['userid']}"
    )
    current_accommodation_data = current_accommodation_response.get("data", None)

    # 默认值：如果没有当前住宿数据，使用默认值
    current_accommodation = {"id": 1, "type": "Shelter"}
    if current_accommodation_data:
        current_accommodation["id"] = current_accommodation_data.get("id", 1)
        current_accommodation["type"] = current_accommodation_data.get(
            "type", "Shelter"
        )

    # 2. 获取角色财务状态
    character_info_response = await make_api_request_async_backend(
        "GET", f"/characters/getById/{state['userid']}"
    )
    character_info = character_info_response.get("data", {})
    financial_status = {"money": character_info.get("money", 0)}

    # 3. 获取所有可用住宿信息并保留必要字段
    accommodations_response = await make_api_request_async_backend(
        "GET", "/dormitory/getAll"
    )
    available_accommodations_raw = accommodations_response.get("data", [])

    # 过滤出必要字段
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

    # 计算每个住宿的 affordable_weeks
    for acc in available_accommodations:
        weekly_rent = acc["weeklyRent"]
        if weekly_rent == 0:
            acc["affordable_weeks"] = 12  # 最大租期
        else:
            affordable_weeks = financial_status["money"] // weekly_rent
            affordable_weeks = min(affordable_weeks, 12)
            acc["affordable_weeks"] = int(affordable_weeks)

    # 初始化失败原因列表
    failure_reasons = []

    max_retries = 5
    retries = 0

    while retries < max_retries:
        # 为 LLM 构建输入
        payload = {
            "character_stats": format_character_data(state["character_stats"]),
            "current_accommodation": current_accommodation,
            "available_accommodations": available_accommodations,
            "financial_status": financial_status,
            "failure_reasons": failure_reasons,  # 传递失败原因列表
        }

        # 调用 LLM
        try:
            accommodation_decision = await accommodation_decision_generator.ainvoke(
                payload
            )
            print("accommodation_decision: ", accommodation_decision)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            failure_reasons.append(
                f"Attempt {retries + 1}: LLM invocation failed with error: {e}"
            )
            retries += 1
            continue

        logger.info(f"🏠 Attempt {retries + 1}:")
        logger.info(f"🏠 Accommodation ID: {accommodation_decision.accommodation_id}")
        logger.info(f"🏠 Lease Weeks: {accommodation_decision.lease_weeks}")
        logger.info(f"🏠 Comments: {accommodation_decision.comments}")

        # 验证选择的住宿是否存在
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

        # 检查租期是否在1-12周
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

        # 检查用户是否能负担得起租金
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
            # 如果可以负担，执行租赁
            rent_data = {
                "characterId": state["userid"],
                "money": financial_status["money"],
                "dormitoryId": accommodation_decision.accommodation_id,
                "leaseWeeks": lease_weeks,
            }
            print("rent_data: ", rent_data)
            # 游戏端
            logger.info(f"🏠 Successfully rented accommodation.")
            break

    else:
        # 如果重试达到上限，仍未找到合适的住宿
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

    # 通知游戏客户端有关住宿变更的信息
    await state["instance"].send_message(
        {
            "characterId": state["userid"],
            "messageName": "accommodationChange",
            "messageCode": 8,
            "data": {
                "accommodationId": accommodation_decision.accommodation_id,
                "leaseWeeks": lease_weeks,
                "comments": accommodation_decision.comments,
            },
        }
    )

    return {
        "decision": {
            "accommodation_id": accommodation_decision.accommodation_id,
            "lease_weeks": lease_weeks,
            "accommodation_comments": accommodation_decision.comments,
        }
    }
