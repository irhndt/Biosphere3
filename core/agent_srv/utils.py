import requests
import os
from json import JSONDecodeError
import asyncio
from dotenv import load_dotenv
import aiohttp
from loguru import logger
import math
import copy

load_dotenv()
GAME_BACKEND_URL = os.getenv("GAME_BACKEND_URL")
GAME_BACKEND_TIMEOUT = int(os.getenv("GAME_BACKEND_TIMEOUT"))
AGENT_BACKEND_URL = os.getenv("AGENT_BACKEND_URL")
DEFAULT_MODEL_TYPE = os.getenv("DEFAULT_MODEL_TYPE")


async def fetch_api_data_async(
    method: str,
    endpoint: str,
    userid: int,
    _logger,
    timeout: int = GAME_BACKEND_TIMEOUT,
) -> dict:
    """
    Make an asynchronous API request with error handling.

    Args:
        method (str): HTTP method (e.g., 'POST').
        endpoint (str): API endpoint.
        userid (int): User ID.
        _logger: The logger instance for logging errors.
        timeout (int): The timeout for the request.

    Returns:
        dict: The API response data if successful, otherwise an empty dict.
    """
    url = f"{AGENT_BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params={"characterId": userid}, timeout=timeout
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, json={"characterId": userid}, timeout=timeout
                ) as response:
                    response.raise_for_status()
                    return await response.json()
    except asyncio.TimeoutError:
        _logger.error(f"Timeout while accessing {endpoint}")
    except aiohttp.ClientError as e:
        _logger.error(f"HTTP error while accessing {endpoint}: {e}")
    except JSONDecodeError:
        _logger.error(f"Failed to decode JSON from {endpoint}")
    return {}


def fetch_json(url: str, timeout: int, _logger, error_message: str = "") -> dict:
    """
    Fetch JSON data from a given URL with error handling.

    Args:
        url (str): The URL to send the GET request to.
        timeout (int): The timeout for the request.
        _logger: The logger instance for logging errors.
        error_message (str): Custom error message for timeout.

    Returns:
        dict: The JSON data if successful, otherwise an empty dict.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response_data = response.json().get("data", {})
        if response_data == None:
            return {"code": 0, "data": None, "message": "Resource not found at GAMEDB"}
        return response_data
    except TimeoutError:
        _logger.error(error_message)
    except JSONDecodeError:
        _logger.error(f"Failed to decode JSON from {url}")
    return {"code": 0, "data": {}, "message": "Resource not found at GAMEDB"}


async def fetch_json_async(
    url: str, timeout: int, _logger, error_message: str = ""
) -> dict:
    """
    Fetch JSON data from a given URL asynchronously with error handling.

    Args:
        url (str): The URL to send the GET request to.
        timeout (int): The timeout for the request.
        _logger: The logger instance for logging errors.
        error_message (str): Custom error message for timeout.

    Returns:
        dict: The JSON data if successful, otherwise an empty dict.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                response_data = await response.json()
                return response_data.get("data", {}) if response_data else {}
    except asyncio.TimeoutError:
        _logger.error(error_message)
    except aiohttp.ClientError as e:
        _logger.error(f"HTTP error while accessing {url}: {e}")
    except JSONDecodeError:
        _logger.error(f"Failed to decode JSON from {url}")
    return {"code": 0, "data": {}, "message": "Resource not found at GAMEDB"}


def get_inventory(userid: int) -> dict:
    response = fetch_json(
        f"{GAME_BACKEND_URL}/bag/getByCharacterId/{userid}",
        timeout=GAME_BACKEND_TIMEOUT,
        _logger=logger,
        error_message="Failed to get inventory from game backend",
    )
    inventory_dict = {}
    try:
        for x in response:
            inventory_dict[x["itemName"]] = x["itemQuantity"]
    except KeyError:
        logger.error("Failed to get inventory from game backend")
    return inventory_dict


async def get_inventory_async(userid: int) -> dict:
    response = await fetch_json_async(
        f"{GAME_BACKEND_URL}/bag/getByCharacterId/{userid}",
        timeout=GAME_BACKEND_TIMEOUT,
        _logger=logger,
        error_message="Failed to get inventory from game backend",
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
    price_response = fetch_json(
        url=f"{GAME_BACKEND_URL}/ammPool/getAveragePrice",
        timeout=GAME_BACKEND_TIMEOUT,
        _logger=logger,
        error_message="Failed to get market data from AMM pool",
    )
    market_data_dict = dict({x["name"]: x["averagePrice"] for x in price_response})
    return market_data_dict


async def get_prompt_data_from_db(userid: int):
    # Prompt data
    prompt_response = await fetch_json_async(
        url=f"{AGENT_BACKEND_URL}/agent_prompt/?characterId={userid}",
        timeout=GAME_BACKEND_TIMEOUT,
        _logger=logger,
        error_message="Failed to get prompt data from game backend",
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
    """
    Asynchronously fetches character data from the game database.

    Args:
        userid (int): The ID of the user.

    Returns:
        dict: The game database character response.
    """
    response = await fetch_json_async(
        f"{GAME_BACKEND_URL}/characters/getByIdS/{userid}",
        timeout=GAME_BACKEND_TIMEOUT,
        _logger=logger,
        error_message="Failed to get character data from game backend",
    )
    return response


async def fetch_agent_db_response_async(userid: int) -> dict:
    """
    Asynchronously fetches character data from the agent database.

    Args:
        userid (int): The ID of the user.

    Returns:
        dict: The agent database response.
    """
    response = await fetch_api_data_async(
        "GET",
        endpoint="/characters/",
        userid=userid,
        _logger=logger,
        timeout=GAME_BACKEND_TIMEOUT,
    )
    if response.get("code") == 0:
        logger.info(
            "🆕 No character data found in agent database, creating new character"
        )
        return {}
    return response.get("data", [])[0]


async def fetch_model_type_response_async(userid: int) -> dict:
    """
    Asynchronously fetches model type from the character model service.

    Args:
        userid (int): The ID of the user.

    Returns:
        dict: The model type response.
    """
    response = await fetch_json_async(
        f"{GAME_BACKEND_URL}/CharacterModel/getByCharacterId/{userid}",
        timeout=GAME_BACKEND_TIMEOUT,
        _logger=logger,
        error_message="Failed to get model type from character model service",
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
            "health": game_db_character_response.get("health"),
            "energy": game_db_character_response.get("energy"),
            "hungry": game_db_character_response.get("hungry"),
            "education": game_db_character_response.get("education"),
            "education_experience": game_db_character_response.get("experience"),
            "money": game_db_character_response.get("money"),
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
    url = f"{AGENT_BACKEND_URL}/actions/"
    data = {
        "characterId": userid,
        "location": action.get("location", ""),
        "gameTime": action.get("gameTime", ""),
    }
    try:
        response = requests.post(
            url,
            json=data,
            timeout=GAME_BACKEND_TIMEOUT,
        )
        response.raise_for_status()
    except requests.Timeout:
        logger.error(f"Timeout while saving action to {url}")
    except requests.HTTPError as e:
        logger.error(f"HTTP error while saving action to {url}: {e}")
    except JSONDecodeError:
        logger.error(f"Failed to decode JSON from {url}")


def save_decision_to_db(userid: int, decision: dict):
    """
    Save the decision to the game database.

    Args:
        userid (int): The ID of the user.
        decision (dict): The decision data to save.
    """
    url = f"{AGENT_BACKEND_URL}/decision/"
    decision["characterId"] = userid
    try:
        response = requests.patch(
            url,
            json=decision,
            timeout=GAME_BACKEND_TIMEOUT,
        )
        response.raise_for_status()
    except requests.Timeout:
        logger.error(f"Timeout while saving decision to {url}")
    except requests.HTTPError as e:
        logger.error(f"HTTP error while saving decision to {url}: {e}")
    except JSONDecodeError:
        logger.error(f"Failed to decode JSON from {url}")


def save_token_consumption_to_db(token_consumption: dict):
    """
    Save the token consumption to the game database.

    Args:
        token_consumption (dict): The token consumption data to save.
    """
    url = f"{GAME_BACKEND_URL}/modelToken/add/"
    for model_type, usage in token_consumption.items():
        data = {
            "modelType": model_type,
            "prompt": usage.get("prompt", 0),
            "completion": usage.get("completion", 0),
            "total": usage.get("total", 0),
        }
        try:
            response = requests.post(
                url,
                json=data,
                timeout=GAME_BACKEND_TIMEOUT,
            )
            response.raise_for_status()
        except requests.Timeout:
            logger.error(f"Timeout while saving token consumption to {url}")
        except requests.HTTPError as e:
            logger.error(f"HTTP error while saving token consumption to {url}: {e}")
        except JSONDecodeError:
            logger.error(f"Failed to decode JSON from {url}")


def get_occupation(job_id: int) -> str:
    occupation_mapping = {
        "0": "Unemployed",
        "1": "Intern",
        "2": "Trainee",
        "3": "Assistant",
        "4": "Programmer",
        "5": "Researcher",
        "6": "Manager",
        "7": "Director",
        "8": "Chief Officer",
        "9": "President",
        "10": "Chairman",
        "11": "Guard",
        "12": "Cleaner",
        "13": "Gardener",
        "14": "Police",
        "15": "Cook",
        "16": "Librarian",
        "17": "Store Clerk",
    }
    return occupation_mapping.get(job_id, "Unemployed")


def get_work_place(job_id: int) -> str:
    work_place_mapping = {
        "0": "N/A",
        "1": "School",
        "2": "School",
        "3": "School",
        "4": "School",
        "5": "School",
        "6": "School",
        "7": "School",
        "8": "School",
        "9": "School",
        "10": "School",
        "11": "School",
        "12": "School",
        "13": "Garden",
        "14": "PoliceStation",
        "15": "Canteen",
        "16": "Library",
        "17": "Supermarket",
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
            "daily_objective": [],
            "meta_seq": [],
            "reflection": [],
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
Constraints: Must in (school,workshop,home,farm,mall,square,councilHall,hospital,fruit,harvest,fishing,mine,orchard,foodfactory,factory,garden,policestation,library,supermarket,canteen).
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
    - book: +10 education experience
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
    "councilHall",
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


def format_level_graph(level_graph_data: dict) -> str:
    formatted_str = ""
    for goal in level_graph_data:
        formatted_str += f"Level {goal['goal_number']}:\n"
        for obj in goal["objectives"]:
            formatted_str += f"  - {obj['item']} *{obj['quantity']}\n"
        formatted_str += "\n"
    return formatted_str.strip()


def update_state_daily(state: dict):
    state["meta"]["day"] += 1
    state["past_stats"] = copy.deepcopy(state["character_stats"])


def clear_decision(state: dict):
    state["decision"]["action_description"] = []
    state["decision"]["action_result"] = []
    state["decision"]["new_plan"] = []
    state["decision"]["daily_objective"] = []
    state["decision"]["meta_seq"] = []
    state["decision"]["reflection"] = []


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
    if "education_experience" in fields and "education_experience" in past_status and "education_experience" in status:
        formatted_data.append(
            f"Education Experience: {past_status.get('education_experience', 'N/A')} -> {status.get('education_experience', 'N/A')}"
        )
    if "money" in fields and "money" in past_status and "money" in status:
        formatted_data.append(
            f"Money: {past_status.get('money', 'N/A')} -> {status.get('money', 'N/A')}"
        )
    if "occupation" in fields and "occupation" in past_status and "occupation" in status:
        formatted_data.append(
            f"Occupation: {past_status.get('occupation', 'N/A')} -> {status.get('occupation', 'N/A')}"
        )
    if "efficiency" in fields and "efficiency" in past_status and "efficiency" in status:
        formatted_data.append(
            f"Efficiency: {past_status.get('efficiency', 'N/A')} -> {status.get('efficiency', 'N/A')}"
        )
    if "inventory" in fields and "inventory" in past_status and "inventory" in status:
        formatted_data.append(
            f"Inventory: {past_status.get('inventory', 'N/A')} -> {status.get('inventory', 'N/A')}"
        )

    return "\n".join(formatted_data)
