from core.conversation_srv.conversation_prompts import *
from core.utils.llm_factory import LLMSelector
from core.conversation_srv.conversation_model import *
from core.db.api_client import agent_api
import random
from datetime import datetime
from loguru import logger

llm_selector = LLMSelector()


def conversation_llm(prompt_template, model_name, output_type, temperature):
    return prompt_template | llm_selector.get_llm(
        model_type="CHAT", model_name=model_name, temperature=temperature
    ).with_structured_output(output_type)


conversation_topic_planner = conversation_llm(
    prompt_template=conversation_topic_planner_prompt,
    model_name="gpt-4o-mini",
    output_type=ConversationTopics,
    temperature=1
)

conversation_generator = conversation_llm(
    prompt_template=conversation_generator_prompt,
    model_name="gpt-4o",
    output_type=ConversationContent,
    temperature=0.5
)

simple_content_generator = conversation_llm(
    prompt_template=simple_content_prompt,
    model_name="gpt-4o",
    output_type=ConversationContent,
    temperature=0.5
)

conversation_check = conversation_llm(
    prompt_template=conversation_check_prompt,
    model_name="gpt-4o-mini",
    output_type=CheckResult,
    temperature=0
)

impression_update = conversation_llm(
    prompt_template=impression_update_prompt,
    model_name="gpt-4o-mini",
    output_type=ImpressionUpdate,
    temperature=1
)

conversation_intimacy_mark = conversation_llm(
    prompt_template=intimacy_mark_prompt,
    model_name="gpt-4o-mini",
    output_type=IntimacyMark,
    temperature=0.5
)


def make_api_request_sync(
    method: str,
    endpoint: str,
    params: dict = None,
    data: dict = None,
):
    response = {}

    try:
        response = agent_api.request_sync(method, endpoint, params, data, False)
    except Exception as e:
        print(f"API request error: {e}")

    if response:
        return response
    else:
        return {"data": None, "message": None}


# a tool for transferring real_time to game_time
def calculate_game_time(real_time=datetime.now(), day1_str="2024-7-1 3:00"):
    day1 = datetime.strptime(day1_str, "%Y-%m-%d %H:%M")
    elapsed_time = real_time - day1
    game_elapsed_time = elapsed_time * 7
    game_day = game_elapsed_time.days
    total_seconds = int(game_elapsed_time.total_seconds())
    remaining_seconds = total_seconds - (game_day * 86400)
    game_hour, remainder = divmod(remaining_seconds, 3600)
    game_minute, seconds = divmod(remainder, 60)
    return [game_day+1, game_hour, game_minute]


# Randomly return k players, excluding the user.
def random_conversation_target(k: int, my_id: int):
    if k == 0:
        return []
    while True:
        try:
            all_player_list = make_api_request_sync("GET", "/characters/ids_and_names")
        except Exception as e:
            logger.error(f"User {my_id} error in selecting conversation target: {e}")
        else:
            break

    all_id_list = []
    for player in all_player_list["data"]:
        if player["characterId"] != my_id:
            all_id_list.append(player["characterId"])

    total_players = len(all_id_list)
    random_id_list = random.sample(range(total_players), k)
    random_player_list = [all_id_list[i] for i in random_id_list]
    return random_player_list


# randomly generate k conversation times from the current time until 10 minutes before the end of the message value
def generate_talk_time(k: int):
    day, hour, minute = calculate_game_time(real_time=datetime.now())

    largest_minute = ((24 - hour) * 60 + (0 - minute)) // 7
    k = min(k - 1, largest_minute // 10) + 1
    time_slot = largest_minute // k

    time_list = []
    sorted_numbers = []
    d = min(5, time_slot // 3)
    for kk in range(k):
        sorted_numbers.append(
            random.randint(kk * time_slot + d, (kk + 1) * time_slot - d) * 7
        )

    # only for test, set the first conversation to happen after 5 minutes in game time
    sorted_numbers[0] = 1

    for t in sorted_numbers:
        add_hour, add_minute = divmod(minute + t, 60)
        if (hour + add_hour) >= 24:
            break
        elif (hour + add_hour) == 23 and add_minute >= 40:
            break
        start_time = f"{(hour+add_hour):02}" + ":" + f"{add_minute:02}"
        time_list.append(start_time)

    return time_list


def mark_map(x: int):
    mapping = {
        5: 8,
        4: 4,
        3: 0,
        2: -3,
        1: -5
    }
    return mapping.get(x, 0)


def strip_relation(impression: str):
    try:
        relation_start = impression.find("relation:") + len("relation:")
        relation_end = impression.find("emotion:")
        relation_info = impression[relation_start:relation_end].strip()
    except Exception as e:
        logger.error(f"Error in stripping relation from impression: {e}")
        relation_info = "Strangers."
        logger.warning(f"Using default relation: {relation_info}")
    return relation_info

def reformat_conversation(raw_conversation: str):
    lines = raw_conversation.strip().split('\n')
    content = []
    for line in lines:
        if line:
            key, value = line.split(':')
            content.append({key.strip(): value.strip()})
    return content