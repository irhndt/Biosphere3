import os
import json
import asyncio
from dotenv import load_dotenv
from loguru import logger
import math
import copy
import pandas as pd
from collections import deque
from core.db.api_client import agent_api, game_api

load_dotenv()
DEFAULT_MODEL_TYPE = os.getenv("DEFAULT_MODEL_TYPE")
skill2actions = json.load(open("core/files/skill2actions.json"))


def get_inventory(userid: int) -> dict:
    response = game_api.request_sync(
        method="GET", endpoint=f"/bag/getByCharacterId/{userid}"
    )
    inventory_dict = {}
    try:
        for x in response:
            inventory_dict[x["itemName"]] = x["itemQuantity"]
    except KeyError:
        logger.error("Failed to get inventory from game backend")
    return inventory_dict


async def get_inventory_async(userid: int) -> dict:
    response = await game_api.request_async(
        method="GET", endpoint=f"/bag/getByCharacterId/{userid}"
    )
    inventory_dict = {}
    try:
        for x in response:
            inventory_dict[x["itemName"]] = x["itemQuantity"]
    except (KeyError, TypeError):
        logger.error("Failed to parse inventory data from game backend")
    return inventory_dict


def get_market_data_from_db() -> dict:
    # Market data
    price_response = game_api.request_sync(
        method="GET", endpoint="/ammPool/getAveragePrice"
    )
    market_data_dict = dict({x["name"]: x["averagePrice"] for x in price_response})
    return market_data_dict


def get_amm_data_from_db() -> dict:
    amm_response = game_api.request_sync(method="GET", endpoint="/ammPool/getAll")
    return amm_response


async def get_prompt_data_from_db(userid: int):
    # Prompt data
    prompt_response = await agent_api.request_async(
        method="GET", endpoint="/agent_prompt/", params={"characterId": userid}
    )
    dict = prompt_response[0] if prompt_response else {}
    fields = [
        "daily_goal",
        "refer_to_previous",
        "life_style",
        "daily_objective_ar",
        "task_priority",
        "max_actions",
        "meta_seq_ar",
        "replan_time_limit",
        "meta_seq_adjuster_ar",
        "focus_topic",
        "depth_of_reflection",
        "reflection_ar",
        "level_of_detail",
        "tone_and_style",
    ]
    return {key: dict[key] for key in fields if key in dict}


async def fetch_game_db_character_response_async(userid: int) -> dict:
    response = await game_api.request_async(
        method="GET", endpoint=f"/characters/getByIdS/{userid}"
    )
    return response


async def fetch_agent_db_response_async(userid: int) -> dict:
    response = await agent_api.request_async(
        method="GET",
        endpoint="/characters/",
        params={"characterId": userid},
        return_data=False,
    )
    if response.get("code") == 0:
        logger.info(
            "🆕 No character data found in agent database, creating new character"
        )
        return {}
    data = response.get("data", [])
    return data[0] if data else {}


async def fetch_model_type_response_async(userid: int) -> dict:
    response = await game_api.request_async(
        method="GET", endpoint=f"/CharacterModel/getByCharacterId/{userid}"
    )
    return response


async def get_character_data_async(userid: int) -> dict:
    # Fetch data concurrently using asyncio.gather
    game_db_task = asyncio.create_task(fetch_game_db_character_response_async(userid))
    agent_db_task = asyncio.create_task(fetch_agent_db_response_async(userid))
    model_type_task = asyncio.create_task(fetch_model_type_response_async(userid))

    game_db_character_response, agent_db_response, model_type_response = (
        await asyncio.gather(game_db_task, agent_db_task, model_type_task)
    )

    # Fetch inventory asynchronously
    inventory = await get_inventory_async(userid)

    # Construct character_data
    try:
        character_data = {
            "name": game_db_character_response.get("characterName"),
            "health": game_db_character_response.get("health"),
            "energy": game_db_character_response.get("energy"),
            "hungry": game_db_character_response.get("hungry"),
            "education": (
                game_db_character_response.get("education")
                if game_db_character_response.get("education") != "None"
                else "PrimarySchool"
            ),
            "education_experience": game_db_character_response.get("experience"),
            "money": game_db_character_response.get("money"),
            "jobId": game_db_character_response.get("jobId"),
            "occupation": get_occupation(game_db_character_response.get("jobId")),
            "work_place": get_work_place(game_db_character_response.get("jobId")),
            "efficiency": compute_efficiency(game_db_character_response),
            "inventory": inventory,
            "personality": agent_db_response.get("personality"),
            "long_term_goal": agent_db_response.get("long_term_goal"),
            "short_term_goal": agent_db_response.get("short_term_goal"),
            "language_style": agent_db_response.get("language_style"),
            "biography": agent_db_response.get("biography"),
            "model_type": model_type_response.get("modelType", DEFAULT_MODEL_TYPE),
        }

    except AttributeError:
        logger.error(f"Failed to get character data")
        return {}

    return character_data


def save_action_to_db(userid: int, action: dict):
    agent_api.request_sync(
        method="POST",
        endpoint="/actions/",
        data={
            "characterId": userid,
            "location": action.get("location", ""),
            "gameTime": action.get("gameTime", ""),
        },
    )


def save_decision_to_db(userid: int, decision: dict, endpoint: str):
    decision["characterId"] = userid
    agent_api.request_sync(
        method="POST",
        endpoint=f"/{endpoint}/",
        data=decision,
    )


def save_reflection_to_db(user_id: int, reflection: dict):
    reflection["characterId"] = user_id
    agent_api.request_sync(
        method="PATCH",
        endpoint="/reflection/",
        data=reflection,
    )


def save_token_consumption_to_db(token_consumption: dict):
    for model_type, usage in token_consumption.items():
        data = {
            "modelType": model_type,
            "prompt": usage.get("prompt", 0),
            "completion": usage.get("completion", 0),
            "total": usage.get("total", 0),
        }
        game_api.request_sync(method="POST", endpoint="/modelToken/add/", data=data)


def get_occupation(job_id: int) -> str:
    occupation_mapping = {
        0: "Unemployed",
        1: "Intern",
        2: "Trainee",
        3: "Assistant",
        4: "Programmer",
        5: "Researcher",
        6: "Manager",
        7: "Director",
        8: "Chief Officer",
        9: "President",
        10: "Chairman",
        11: "Guard",
        12: "Cleaner",
        13: "Gardener",
        14: "Police",
        15: "Cook",
        16: "Librarian",
        17: "Store Clerk",
    }

    return occupation_mapping.get(job_id, "Unemployed")


def get_work_place(job_id: int) -> str:
    work_place_mapping = {
        0: "N/A",
        1: "school",  # Intern
        2: "school",  # Trainee
        3: "school",  # Assistant
        4: "office",  # Programmer
        5: "school",  # Researcher
        6: "office",  # Manager
        7: "office",  # Director
        8: "office",  # ChiefOfficer
        9: "office",  # President
        10: "office",  # Chairman
        11: "school",  # Guard
        12: "square",  # Cleaner
        13: "garden",  # Gardener
        14: "policestation",  # Police
        15: "canteen",  # Cook
        16: "library",  # Librarian
        17: "supermarket",  # StoreClerk
    }
    return work_place_mapping.get(job_id, "N/A")


def compute_efficiency(character_data: dict) -> float:
    hungry = (
        character_data.get("hungry", 0) / 100
        if character_data.get("hungry", 0) < 50
        else 1
    )
    energy = character_data.get("energy", 0) / 100
    health = character_data.get("health", 0) / 100
    wisdom = math.log(character_data.get("education_experience", 0) + 10, 10)
    return hungry * energy * health * wisdom


async def get_initial_state_from_db(userid, websocket):
    market_data = get_market_data_from_db()
    character_data = await get_character_data_async(userid)
    prompt_data = await get_prompt_data_from_db(userid)
    state = {
        "userid": userid,
        "character_stats": character_data,
        "public_data": {"market_data": market_data},
        "decision": {
            "need_replan": False,
            "action_description": [],
            "action_result": [],
            "new_plan": [],
            "daily_objective": deque(maxlen=10),
            "trade_objective": [],
            "meta_seq": [],
            "reflection": [],
            "expanded_meta_seq": deque(),
            "cv": {
                "job_id": 0,
                "content": "",
            },
        },
        "meta": {
            "tool_functions": tool_functions_live,
            "day": 0,
            "available_locations": available_locations,
        },
        "past_stats": {},
        "prompts": prompt_data,
        "message_queue": asyncio.Queue(),
        "event_queue": asyncio.Queue(),
        "false_action_queue": asyncio.Queue(),
        "websocket": websocket,
        "current_pointer": "Sensing_Route",
    }
    return state


tool_functions_live = """
1. goto [placeName:string]: Go to a specified location.
Constraints: Must in (school,workshop,home,farm,mall,square,councilhall,hospital,fruit,harvest,fishing,mine,orchard,foodfactory,factory,garden,policestation,library,supermarket,canteen).
2. sleep [hours:int]: Sleep to recover energy (10 per hour).
Constraints: Must be at home.
3. study [hours:int]: Study to achieve a higher degree, cost money (100 per hour) and energy (10 per hour), gain education experience (10 per hour).
Constraints: Must be in school and have enough money.
4. seedoctor [hours:int]: See a doctor, cost money (100 per hour), gain health (10 per hour).
Constraints: Must be in the hospital and have enough money.
5. work [hours:int]: Work to earn money (you should check your salary per hour), cost energy (10 per hour).
Constraints: Must have an occupation and be in the corresponding work place.
6. use [itemType:string] [amount:int]: Use items in your inventory to get corresponding effects. Here are the effects of different items:
    - apple: +10 hungry
    - pear: +15 hungry
    - bread: +25 hungry
    - applepie: +20 hungry
    - fruitsalad: +35 hungry
    - chickensalad: +35 hungry and +10 energy
    - beefrice: +50 hungry and +5 energy
    - sushi: +30 hungry
    - books: +10 education experience
Constraints: Must have enough items in inventory.
7. buy [itemType:string] [amount:int]: Purchase items, costing money (you should check the market data to get the price of different items).
Constraints: Must have enough money, and items must be available in sufficient quantity in the AMM.
8. sell [itemType:string] [amount:int]: Sell items to get money (you should check the market data to get the price of different items).
Constraints: Must have enough items in inventory.
"""

available_locations = [
    "school",
    "workshop",
    "home",
    "farm",
    "mall",
    "square",
    "councilhall",
    "hospital",
    "fruit",
    "harvest",
    "fishing",
    "mine",
    "orchard",
    "foodfactory",
    "factory",
    "garden",
    "policestation",
    "library",
    "supermarket",
    "canteen",
]


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


def format_character_data(character_data: dict, fields: list = None) -> str:
    if fields is None:
        fields = character_data.keys()

    formatted_data = []

    if "health" in fields and "health" in character_data:
        formatted_data.append(
            f"Health: {character_data.get('health', 'N/A')} - Represents the character's physical well-being. The range is 0 to 100"
        )
    if "energy" in fields and "energy" in character_data:
        formatted_data.append(
            f"Energy: {character_data.get('energy', 'N/A')} - Indicates how much energy the character has left. The range is 0 to 100"
        )
    if "hungry" in fields and "hungry" in character_data:
        formatted_data.append(
            f"Hungry: {character_data.get('hungry', 'N/A')} - Indicates the character's level of satiety; the higher, the fuller. The range is 0 to 100"
        )
    if "education" in fields and "education" in character_data:
        formatted_data.append(f"Education: {character_data.get('education', 'N/A')}")
    if "education_experience" in fields and "education_experience" in character_data:
        formatted_data.append(
            f"Education Experience: {character_data.get('education_experience', 'N/A')}"
        )
    if "money" in fields and "money" in character_data:
        formatted_data.append(f"Money: {character_data.get('money', 'N/A')}")
    if "occupation" in fields and "occupation" in character_data:
        formatted_data.append(
            f"Occupation: {character_data.get('occupation', 'N/A')} - Current job or role work at {character_data.get('work_place', 'N/A')}"
        )
    if "efficiency" in fields and "efficiency" in character_data:
        formatted_data.append(
            f"Efficiency: {character_data.get('efficiency', 'N/A'):.2f} - Calculated efficiency based on various factors: "
            f"Efficiency = (Hungry Factor) * (Energy Factor) * (Health Factor) * (Wisdom Factor), where:\n"
            f"  - Hungry Factor = hungry / 100 if hungry < 50 else 1\n"
            f"  - Energy Factor = energy / 100\n"
            f"  - Health Factor = health / 100\n"
            f"  - Wisdom Factor = log(education_experience + 10, 10)\n"
            f"  Efficiency affects the crafting efficiency of items. If the efficiency is too low (lower than 0.2), "
            f"  it is advisable to improve the basic attributes first."
        )
    if "inventory" in fields and "inventory" in character_data:
        formatted_data.append(f"Inventory: {character_data.get('inventory', {})}")
    if "personality" in fields and "personality" in character_data:
        formatted_data.append(
            f"Personality: {character_data.get('personality', 'N/A')}"
        )
    if "long_term_goal" in fields and "long_term_goal" in character_data:
        formatted_data.append(
            f"Long-term Goal: {character_data.get('long_term_goal', 'N/A')}"
        )
    if "short_term_goal" in fields and "short_term_goal" in character_data:
        formatted_data.append(
            f"Short-term Goal: {character_data.get('short_term_goal', 'N/A')}"
        )
    if "language_style" in fields and "language_style" in character_data:
        formatted_data.append(
            f"Language Style: {character_data.get('language_style', 'N/A')}"
        )
    if "biography" in fields and "biography" in character_data:
        formatted_data.append(f"Biography: {character_data.get('biography', 'N/A')}")

    return "\n".join(formatted_data)


def format_conversation_data(user_id, conversation_data: list) -> str:
    if not conversation_data or len(conversation_data) == 0:
        return "No conversation data available."

    formatted_conversations = []
    for conversation in conversation_data:
        if conversation["from_id"] == user_id:
            formatted_conversations.append(
                f"Said to {conversation['to_id']}: {conversation['message']}"
            )
        elif conversation["to_id"] == user_id:
            formatted_conversations.append(
                f"{conversation['from_id']} said to me: {conversation['message']}"
            )
        else:
            formatted_conversations.append(
                f"{conversation['from_id']} -> {conversation['to_id']}: {conversation['message']}"
            )

    return "\n".join(formatted_conversations)


async def format_queue_data(queue_data: asyncio.Queue) -> str:
    if not queue_data or queue_data.empty():
        return "No data available."
    items = []
    while queue_data.empty() is False:
        item = await queue_data.get()
        items.append(str(item))
    return ", ".join(items)


def format_level_graph(
    level_graph_data: dict, inventory_info: dict, current_energy: int
) -> str:
    formatted_str = f"Current Energy: {current_energy}\n"
    inventory_copy = inventory_info.copy()
    inventory_copy = {key.lower(): value for key, value in inventory_copy.items()}

    def get_cost(skill2actions, item):
        # print(item)
        for _, details in skill2actions.items():
            if item in details["materials"].keys():
                return details["cost"]
        return 20

    formatted_str += "Final Product: " + level_graph_data["final_product"] + "\n"
    level_graph_data_list = level_graph_data["goals"]
    for goal in level_graph_data_list:
        formatted_str += f"Level {goal['goal_number']}:\n"
        for obj in goal["objectives"]:
            formatted_str += f"  - {obj['item']} *{obj['quantity']}\n"
            formatted_str += f"     | Inventory: {inventory_copy.get(obj['item'], 0)}, Lack {obj['quantity'] - inventory_copy.get(obj['item'], 0)}\n"
            energy_cost = get_cost(skill2actions, obj["item"])
            formatted_str += f"     | Energy Cost: {energy_cost} per item, max craft num {current_energy / energy_cost} \n"
        formatted_str += "\n"
    return formatted_str


def format_trade_and_craft_sequence(trade_and_craft_sequence: list):
    formatted_str = ""
    for action in trade_and_craft_sequence:
        formatted_str += f"Action: {action['action']}\n"
        formatted_str += f" | Reason: {action['reason']}\n"
        if action.get("cost"):
            formatted_str += f" | Cost: {action['cost']}\n"
        if action.get("expected_revenue"):
            formatted_str += f" | Expected Revenue: {action['expected_revenue']}\n"
        formatted_str += "---\n"
    return formatted_str.strip()


def format_dict(data: dict) -> str:
    return "\n".join([f"{key}: {value}" for key, value in data.items()])


def format_market(market_data: dict) -> str:
    formatted_str = "{\n"
    items = list(market_data.items())
    for i in range(0, len(items), 4):
        chunk = items[i : i + 4]
        line = ", ".join([f"{item.lower()}: {price}" for item, price in chunk])
        formatted_str += f" {line}\n"
    formatted_str += "}"
    return formatted_str


def format_daily_obj(daily_objectives: deque) -> str:
    formatted_str = ""
    if not daily_objectives:
        return formatted_str
    for i, obj in enumerate(daily_objectives, start=1):
        formatted_str += f"Objective {i}: {obj}\n"
    return formatted_str


def update_state_daily(state: dict, day: int):
    state["meta"]["day"] = day
    state["past_stats"] = copy.deepcopy(state["character_stats"])


def clear_decision(state: dict):
    state["decision"]["action_description"].clear()
    state["decision"]["action_result"].clear()
    state["decision"]["new_plan"].clear()
    state["decision"]["meta_seq"].clear()
    # state["decision"]["expanded_meta_seq"].clear()
    # state["decision"]["trade_objective"].clear()
    state["decision"]["reflection"].clear()

    # if "daily_objective" in state["decision"]:
    #     state["decision"]["daily_objective"].clear()
    # else:
    #     state["decision"]["daily_objective"] = deque(maxlen=10)


def format_status_changes(past_status: dict, status: dict, fields: list = None) -> str:
    if fields is None:
        fields = status.keys()

    formatted_data = []

    if "health" in fields and "health" in past_status and "health" in status:
        formatted_data.append(
            f"Health: {past_status.get('health', 'N/A')} -> {status.get('health', 'N/A')}"
        )
    if "energy" in fields and "energy" in past_status and "energy" in status:
        formatted_data.append(
            f"Energy: {past_status.get('energy', 'N/A')} -> {status.get('energy', 'N/A')}"
        )
    if "hungry" in fields and "hungry" in past_status and "hungry" in status:
        formatted_data.append(
            f"Hungry: {past_status.get('hungry', 'N/A')} -> {status.get('hungry', 'N/A')}"
        )
    if "education" in fields and "education" in past_status and "education" in status:
        formatted_data.append(
            f"Education: {past_status.get('education', 'N/A')} -> {status.get('education', 'N/A')}"
        )
    if (
        "education_experience" in fields
        and "education_experience" in past_status
        and "education_experience" in status
    ):
        formatted_data.append(
            f"Education Experience: {past_status.get('education_experience', 'N/A')} -> {status.get('education_experience', 'N/A')}"
        )
    if "money" in fields and "money" in past_status and "money" in status:
        formatted_data.append(
            f"Money: {past_status.get('money', 'N/A')} -> {status.get('money', 'N/A')}"
        )
    if (
        "occupation" in fields
        and "occupation" in past_status
        and "occupation" in status
    ):
        formatted_data.append(
            f"Occupation: {past_status.get('occupation', 'N/A')} -> {status.get('occupation', 'N/A')}"
        )
    if (
        "efficiency" in fields
        and "efficiency" in past_status
        and "efficiency" in status
    ):
        formatted_data.append(
            f"Efficiency: {past_status.get('efficiency', 'N/A')} -> {status.get('efficiency', 'N/A')}"
        )
    if "inventory" in fields and "inventory" in past_status and "inventory" in status:
        formatted_data.append(
            f"Inventory: {past_status.get('inventory', 'N/A')} -> {status.get('inventory', 'N/A')}"
        )

    return "\n".join(formatted_data)


def format_false_action_info(false_action_info: dict) -> str:
    formatted_str = "Failed Action: " + false_action_info["actionName"] + "\n"
    formatted_str += "| Result: " + false_action_info["msg"] + "\n"
    formatted_str += "------\n"
    return formatted_str


def format_meta_seq(meta_seq: list, false_action_name: str) -> str:
    formatted_str = ""
    # find the location of the false action
    false_action_index = 0
    for i, action in enumerate(meta_seq):
        if action == false_action_name:
            false_action_index = i
            break
    meta_seq = meta_seq[false_action_index:]
    for i, action in enumerate(meta_seq, start=1):
        formatted_str += f"Action {i}: {action}\n"
    return formatted_str


def format_detailed_meta_seq(detailed_seq: list, false_action_name: str) -> str:
    formatted_str = ""
    # find the location of the false action
    false_action_index = 0
    for i, action in enumerate(detailed_seq):
        if action["action"] == false_action_name:
            false_action_index = i
            break
    detailed_seq = detailed_seq[false_action_index:]
    for i, action in enumerate(detailed_seq, start=1):
        formatted_str += f"Action {i}: {action['action']}\n"
        if action.get("cost"):
            formatted_str += f" | Cost: {action['cost']}\n"
        if action.get("status_before"):
            formatted_str += f" | Status Before: {action['status_before']}\n"
        if action.get("status_after"):
            formatted_str += f" | Status After: {action['status_after']}\n"
        if action.get("inventory_before"):
            formatted_str += f" | Inventory Before: {action['inventory_before']}\n"
        if action.get("inventory_after"):
            formatted_str += f" | Inventory After: {action['inventory_after']}\n"
        if action.get("reason"):
            formatted_str += f" | Reason: {action['reason']}\n"
        formatted_str += "------\n"
    return formatted_str


def format_meta_seq(meta_seq: list) -> str:
    formatted_str = ""
    for i, action in enumerate(meta_seq, start=1):
        formatted_str += f"Action {i}: {action}\n"
    return formatted_str


def refine_craft_action(craft_action: str) -> str:
    args = craft_action.split()
    craft_item = args[1]
    craft_num = args[2]
    item_templates = {
        "apple": "Pick {0} apple(s)",
        "wheat": "Harvest {0} wheat(s)",
        "pear": "Pick {0} pear(s)",
        "rice": "Harvest {0} rice(s)",
        "chicken": "Raise {0} chicken(s)",
        "beef": "Raise {0} beef(s)",
        "fish": "Catch {0} fish(es)",
        "feed": "Make {0} feed(s)",
        "flour": "Mill {0} flour(s)",
        "bread": "Bake {0} bread(s)",
        "apple_pie": "Bake {0} apple pie(s)",
        "fruit_salad": "Make {0} fruit salad(s)",
        "chicken_salad": "Make {0} chicken salad(s)",
        "beef_rice": "Cook {0} beef rice(s)",
        "sushi": "Make {0} sushi(es)",
        "iron_ore": "Mine {0} iron ore(s)",
        "wood": "Chop {0} wood(s)",
        "copper_ore": "Mine {0} copper ore(s)",
        "silicon_ore": "Mine {0} silicon ore(s)",
        "iron_ingot": "Smelt {0} iron ingot(s)",
        "wooden_board": "Craft {0} wooden board(s)",
        "copper_ingot": "Smelt {0} copper ingot(s)",
        "pure_silicon": "Refine {0} pure silicon(s)",
        "tools": "Craft {0} tool(s)",
        "iron_plate": "Forge {0} iron plate(s)",
        "pulp": "Make {0} pulp(s)",
        "books": "Print {0} book(s)",
        "copper_wire": "Craft {0} copper wire(s)",
        "transistor": "Make {0} transistor(s)",
        "circuit_board": "Assemble {0} circuit board(s)",
        "a100": "Manufacture {0} A100(s)",
        "h100": "Manufacture {0} H100(s)",
        "h200": "Manufacture {0} H200(s)",
        "b200": "Manufacture {0} B200(s)",
    }

    return item_templates[craft_item].replace("{0}", craft_num)


def refine_list(action_list: list) -> list:
    new_list = []
    for action in action_list:
        if action.startswith("craft"):
            new_list.append(refine_craft_action(action))
        else:
            new_list.append(action)
    return new_list


def filter_jobs(all_public_jobs, education, experience):
    education_order = [
        "None",
        "PrimarySchool",
        "SecondarySchool",
        "University",
        "Master",
        "Doctorate",
    ]

    try:
        role_edu_index = education_order.index(education)
    except ValueError:
        return {}
    eligible_jobs = {}
    for job in all_public_jobs:
        job_edu_index = education_order.index(job["education"])
        if role_edu_index >= job_edu_index and experience >= job["experience"]:

            filtered_job = {
                "id": job["id"],
                "jobType": job["jobType"],
                "jobPlace": job["jobPlace"],
                "dailyWages": job["dailyWages"],
                "education": job["education"],
                "wagePerHour": job["wagePerHour"],
                # "populationRatioCap": job["populationRatioCap"],
            }
            eligible_jobs[job["jobName"]] = filtered_job

    return eligible_jobs


def convert_to_table_string(dict_data):
    if not dict_data:
        return None
    df = pd.DataFrame.from_dict(dict_data, orient="index")
    return df.to_string()


def get_industry_and_goal(character_industry: str):
    industry = {"Manufacture": "industry", "Study": "academia", "Food": "business"}

    industry_goal_for_cv = {
        "Manufacture": "Working to make money to produce A100",
        "Study": "Working to make money to fund studies",
        "Food": "Working to make money",
    }
    return industry[character_industry], industry_goal_for_cv[character_industry]


def get_job_name(job_id: int, all_public_jobs: list):
    for job in all_public_jobs:
        if job["id"] == job_id:
            return job["jobName"]
    return "Unemployed"


def get_item_str(price_response: list):
    energy_dict = {
        "apple": {"energy_cost": 3, "recipe": None, "special_effect": "Hungry +10"},
        "wheat": {"energy_cost": 2, "recipe": None, "special_effect": "-"},
        "pear": {"energy_cost": 3, "recipe": None, "special_effect": "Hungry +15"},
        "rice": {"energy_cost": 3, "recipe": None, "special_effect": "-"},
        "chicken": {"energy_cost": 5, "recipe": "1 × feed", "special_effect": "-"},
        "beef": {"energy_cost": 5, "recipe": "3 × feed", "special_effect": "-"},
        "fish": {"energy_cost": 3, "recipe": None, "special_effect": "-"},
        "feed": {"energy_cost": 5, "recipe": "1 × rice", "special_effect": "-"},
        "flour": {"energy_cost": 3, "recipe": "1 × wheat", "special_effect": "-"},
        "bread": {
            "energy_cost": 3,
            "recipe": "1 × flour",
            "special_effect": "Hungry +25",
        },
        "apple_pie": {
            "energy_cost": 3,
            "recipe": "1 × apple, 1 × flour",
            "special_effect": "Hungry +20",
        },
        "fruit_salad": {
            "energy_cost": 5,
            "recipe": "1 × apple, 1 × pear",
            "special_effect": "Hungry +35",
        },
        "chicken_salad": {
            "energy_cost": 10,
            "recipe": "1 × chicken, 1 × fruit_salad",
            "special_effect": "Hungry +35, Energy +10",
        },
        "beef_rice": {
            "energy_cost": 10,
            "recipe": "1 × beef, 1 × rice",
            "special_effect": "Hungry +50, Energy +5",
        },
        "sushi": {
            "energy_cost": 7,
            "recipe": "1 × fish, 1 × rice",
            "special_effect": "Hungry +30",
        },
        "iron_ore": {"energy_cost": 1, "recipe": None, "special_effect": "-"},
        "wood": {"energy_cost": 1, "recipe": None, "special_effect": "-"},
        "copper_ore": {"energy_cost": 1, "recipe": None, "special_effect": "-"},
        "silicon_ore": {"energy_cost": 1, "recipe": None, "special_effect": "-"},
        "iron_ingot": {
            "energy_cost": 5,
            "recipe": "3 × iron_ore",
            "special_effect": "-",
        },
        "wooden_board": {"energy_cost": 5, "recipe": "3 × wood", "special_effect": "-"},
        "copper_ingot": {
            "energy_cost": 5,
            "recipe": "3 × copper_ore",
            "special_effect": "-",
        },
        "pure_silicon": {
            "energy_cost": 5,
            "recipe": "3 × silicon_ore",
            "special_effect": "-",
        },
        "iron_plate": {
            "energy_cost": 5,
            "recipe": "1 × iron_ingot",
            "special_effect": "-",
        },
        "pulp": {"energy_cost": 5, "recipe": "1 × wooden_board", "special_effect": "-"},
        "books": {
            "energy_cost": 10,
            "recipe": "3 × pulp",
            "special_effect": "Education Experience +20",
        },
        "copper_wire": {
            "energy_cost": 5,
            "recipe": "1 × copper_ingot",
            "special_effect": "-",
        },
        "transistor": {
            "energy_cost": 5,
            "recipe": "1 × pure_silicon",
            "special_effect": "-",
        },
        "circuit_board": {
            "energy_cost": 20,
            "recipe": "1 × iron_plate, 2 × copper_wire",
            "special_effect": "-",
        },
        "a100": {
            "energy_cost": 20,
            "recipe": "2 × circuit_board, 2 × transistor",
            "special_effect": "1 unit of GPU",
        },
        "h100": {
            "energy_cost": 25,
            "recipe": "2 × a100",
            "special_effect": "2 units of GPU",
        },
        "h200": {
            "energy_cost": 50,
            "recipe": "2 × h100",
            "special_effect": "4 units of GPU",
        },
        "b200": {
            "energy_cost": 100,
            "recipe": "2 × h200",
            "special_effect": "8 units of GPU",
        },
    }
    price_dict = {}
    for item in price_response:
        std_name = item["name"].lower()
        price_dict[std_name] = item["averagePrice"]
    table_data = []
    for std_name, energy_info in energy_dict.items():
        row = {
            "name": std_name,
            "direct_upstream_materials": energy_info["recipe"] or "",
            "energy_consumed_by_direct_upstream_materials": energy_info["energy_cost"],
            "average_price": price_dict.get(std_name, None),
        }
        table_data.append(row)

    item_str = "# Item Info\n" + pd.DataFrame(table_data).to_string()

    return item_str


def get_production_path_str():
    production_path = {
        "chicken": "4 × rice → 2 × feed → 1 × chicken",
        "beef": "6 × rice → 3 × feed → 1 × beef",
        "feed": "2 × rice → 1 × feed",
        "flour": "2 × wheat → 1 × flour",
        "bread": "4 × wheat → 2 × flour → 1 × bread",
        "apple_pie": "1 × apple, 2 × wheat → 1 × flour, 1 × apple → 1 × apple_pie",
        "fruit_salad": "1 × apple, 1 × pear → 1 × fruit_salad",
        "chicken_salad": "1 × apple, 1 × pear, 8 × rice → 4 × feed, 1 × fruit_salad → 2 × chicken, 1 × fruit_salad → 1 × chicken_salad",
        "beef_rice": "8 × rice → 3 × feed → 1 × beef, 2 × rice → 1 × beef_rice",
        "sushi": "1 × fish, 1 × rice → 1 × sushi",
        "iron_ingot": "3 × iron_ore → 1 × iron_ingot",
        "wooden_board": "3 × wood → 1 × wooden_board",
        "copper_ingot": "3 × copper_ore → 1 × copper_ingot",
        "pure_silicon": "3 × silicon_ore → 1 × pure_silicon",
        "iron_plate": "6 × iron_ore → 2 × iron_ingot → 1 × iron_plate",
        "pulp": "6 × wood → 2 × wooden_board → 1 × pulp",
        "books": "18 × wood → 6 × wooden_board → 3 × pulp → 1 × books",
        "copper_wire": "6 × copper_ore → 2 × copper_ingot → 1 × copper_wire",
        "transistor": "6 × silicon_ore → 2 × pure_silicon → 1 × transistor",
        "circuit_board": "12 × copper_ore, 12 × iron_ore → 4 × copper_ingot, 4 × iron_ingot → 2 × copper_wire, 2 × iron_plate → 1 × circuit_board",
        "a100": "24 × copper_ore, 24 × iron_ore, 12 × silicon_ore → 8 × copper_ingot, 8 × iron_ingot, 4 × pure_silicon → 4 × copper_wire, 4 × iron_plate, 2 × transistor → 2 × circuit_board, 2 × transistor → 1 × a100",
        "h100": "48 × copper_ore, 48 × iron_ore, 24 × silicon_ore → 16 × copper_ingot, 16 × iron_ingot, 8 × pure_silicon → 8 × copper_wire, 8 × iron_plate, 4 × transistor → 4 × circuit_board, 4 × transistor → 2 × a100 → 1 × h100",
        "h200": "96 × copper_ore, 96 × iron_ore, 48 × silicon_ore → 32 × copper_ingot, 32 × iron_ingot, 16 × pure_silicon → 16 × copper_wire, 16 × iron_plate, 8 × transistor → 8 × circuit_board, 8 × transistor → 4 × a100 → 2 × h100 → 1 × h200",
        "b200": "192 × copper_ore, 192 × iron_ore, 96 × silicon_ore → 64 × copper_ingot, 64 × iron_ingot, 32 × pure_silicon → 32 × copper_wire, 32 × iron_plate, 16 × transistor → 16 × circuit_board, 16 × transistor → 8 × a100 → 4 × h100 → 2 × h200 → 1 × b200",
    }
    production_path_str = "# Production Path\n" + "\n".join(
        [f"{item}: {path}" for item, path in production_path.items()]
    )
    return production_path_str


def get_job_str():
    job_data = {
        "Job Title": [
            "Intern",
            "Trainee",
            "Assistant",
            "Programmer",
            "Researcher",
            "Manager",
            "Director",
            "Chief Officer",
            "President",
            "Chairman",
            "Guard",
            "Cleaner",
            "Gardener",
            "Police",
            "Cook",
            "Librarian",
            "Store Clerk",
        ],
        "Hourly Income": [
            30,
            30,
            50,
            40,
            50,
            80,
            100,
            150,
            200,
            250,
            15,
            15,
            25,
            40,
            25,
            40,
            25,
        ],
        "Minimum Education Experience": [
            40,
            40,
            80,
            60,
            80,
            140,
            200,
            350,
            500,
            700,
            10,
            10,
            30,
            60,
            30,
            60,
            30,
        ],
    }

    # Convert the dictionary into a DataFrame
    job_str = "# Job Info\n" + pd.DataFrame(job_data).to_string()
    return job_str


def get_character_data_str(characterId: int, character_data: dict) -> str:
    dormitory_data = game_api.request_sync(
        "GET", f"/characterDormitory/getByCharacterIdNew/{characterId}"
    )
    
    if not dormitory_data:  # 如果返回结果是 None 或者空值
        dormitoryId = None
    else:
        dormitoryId = dormitory_data.get("dormitoryId")
    
    # 如果 dormitoryId 为 None，则返回一些默认数据或处理错误
    if dormitoryId:
        dormitory = game_api.request_sync("GET", f"/dormitory/getById/{dormitoryId}")
    else:
        dormitory = {}

    formatted_data = []
    formatted_data.append(f"Name: {character_data.get('name', 'N/A')}")
    formatted_data.append(f"Biography: {character_data.get('biography', 'N/A')}")
    formatted_data.append(
        f"Health: {character_data.get('health', 'N/A')} - The range is 0 to {dormitory.get('maxHealth', '60')}; It costs 50 money for a visit to the doctor, restoring 20 health points."
    )
    formatted_data.append(
        f"Energy: {character_data.get('energy', 'N/A')} - The range is 0 to {dormitory.get('maxEnergy', '60')}; Sleeping restores {dormitory.get('energyRecovery', 'N/A')} energy points per hour."
    )
    formatted_data.append(
        f"Hungry: {character_data.get('hungry', 'N/A')} - The range is 0 to {dormitory.get('maxHungry', '60')}; Indicates the character's level of satiety; the higher, the fuller."
    )
    formatted_data.append(
        f"Education Experience: {character_data.get('education_experience', 'N/A')} - Studying consumes 3 energy, 50 money per hour, and grants 5 Education Experience. Using a book can directly increase 20 Education Experience."
    )
    formatted_data.append(f"Money: {character_data.get('money', 'N/A')}")
    job_id = character_data.get("jobId", None)
    if job_id:
        wagePerHour = game_api.request_sync("GET", f"/publicWork/getById/{job_id}").get(
            "wagePerHour", 'N/A'
        )
        formatted_data.append(
            f"Occupation: {character_data.get('occupation', 'N/A')} - Working consumes 3 energy per hour and earns {wagePerHour} money."
        )
    formatted_data.append(f"Inventory: {character_data.get('inventory', {})}")

    return "\n".join(formatted_data)



if __name__ == "__main__":
    # print(refine_craft_action("craft rice 2"))
    list_1 = [
        "goto farm",
        "craft rice 7",
        "craft rice 3",
        "goto home",
        "sleep 3",
        "goto farm",
        "craft rice 2",
        "goto home",
        "sleep 3",
        "goto foodfactory",
        "craft feed 6",
    ]
    print(refine_list(list_1))
