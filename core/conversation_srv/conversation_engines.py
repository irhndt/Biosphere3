from core.conversation_srv.conversation_utils import *
from loguru import logger
from typing import Literal
import websockets
import json
from core.conversation_srv.conversation_utils import make_api_request_sync
from core.db.game_api_utils import (
    make_api_request_sync as make_backend_api_request_sync,
)
from datetime import datetime
import random
from langgraph.graph import StateGraph

logger.add(
    "conversation_engines.log",
    format="{time} {level} {message}",
)


async def generate_daily_conversation_plan(state: ConversationState):
    # reset the task list
    state["daily_task"] = []

    # update profile
    userid = state["userid"]
    character_data = {"characterId": userid}
    profile = make_api_request_sync(
        "GET", "/characters/", params=character_data
    )
    if not profile["data"]:
        state["character_stats"] = {}
    else:
        state["character_stats"] = profile["data"][0]
    logger.info(f"User {state['userid']}: {profile['message']}")
    logger.info(f"User {state['userid']} current state is: {state['character_stats']}")

    # get conversation number
    ie_data = {"characterId": state['userid']}
    ie_response = make_api_request_sync(
        "GET", "/conversation_prompt/", params=ie_data
    )
    if ie_response["data"]:
        ie = ie_response["data"][0]["personality"]
    else:
        ie = "Introversion"
    if ie == "Extraversion":
        conversation_number = random.randint(3, 5)
    else:
        conversation_number = random.randint(1, 3)

    # generate conversation time list
    start_time_list = []
    try:
        start_time_list = generate_talk_time(conversation_number)
        if not start_time_list:
            raise ValueError("It's too late. I should start socializing next day.")
    except ValueError as e:
        logger.error(f"⛔ User {state['userid']} Error in planning conversation time: {e}")

    logger.info(f"User {state['userid']} planned start time is {start_time_list}")

    # generate conversation target list
    conversation_number = len(start_time_list)
    target_list = random_conversation_target(conversation_number, state["userid"])
    # target_list[0] = 616422#test
    logger.info(
        f"User {state['userid']} planned to have conversation with {target_list}."
    )

    conversation_plan = DailyConversationPlan(conversations=[])

    if start_time_list:
        for index, start_time in enumerate(start_time_list):
            talk = ""
            to_id = target_list[index]
            # reconstruct the format
            single_conversation = ConversationTask(
                from_id=state["userid"],
                to_id=to_id,
                start_time=start_time,
                topic=talk,
                Finish=[False, False],
            )
            conversation_plan.conversations.append(single_conversation)

        # update daily conversation plan to state
        state["daily_task"] = conversation_plan.conversations

        logger.info(f"🧠 NEW CONVERSATION PLAN GENERATED...")
        logger.info(
            f"New conversation plan of User {state['userid']}: {state['daily_task']}"
        )
    return state


async def start_conversation(state: ConversationState):
    if not state["daily_task"]:
        return state
    current_talk = state["daily_task"][0]  # waiting for check
    logger.info(f"User {state['userid']}: current conversation task is {current_talk}.")
    game_start_time = current_talk["start_time"]
    time_obj = datetime.strptime(game_start_time, "%H:%M")
    start_hour = time_obj.hour
    start_minute = time_obj.minute
    current_time = calculate_game_time(datetime.now())
    if current_time[1] < start_hour or (
        current_time[1] == start_hour and current_time[2] < start_minute
    ):
        sleep_time = (
            (-current_time[1] + start_hour) * 60 * 60
            + (-current_time[2] + start_minute) * 60
        ) // 7
        logger.info(
            f"User {state['userid']}: next conversation will be started after {sleep_time} seconds."
        )
        await asyncio.sleep(sleep_time - 5)
    else:
        logger.info(
            f"User {state['userid']} missed one conversation. Start this task right now..."
        )
        current_talk["start_time"] = (
            f"{current_time[1]:02}" + ":" + f"{current_time[2]:02}"
        )

    # update profile
    userid = state["userid"]
    character_data = {"characterId": userid}
    profile = make_api_request_sync("GET", "/characters/", params=character_data)
    if not profile["data"]:
        state["character_stats"] = {}
    else:
        state["character_stats"] = profile["data"][0]
    logger.info(f"User {state['userid']}: {profile['message']}")
    logger.info(f"User {state['userid']} current state is: {state['character_stats']}")

    # ensure that this target is not the one whom the agent is talking with
    talking_data = {
        "to_id": state["userid"],
        "start_day": current_time[0]
    }
    talking_response = make_api_request_sync(
        "GET", "/conversation/", params=talking_data
    )
    if talking_response["data"]:
        talking_conversation = talking_response["data"][0]
        talking_id = talking_conversation["from_id"]
        if talking_id == current_talk["to_id"]:
            replace_id_list = random_conversation_target(2, state["userid"])
            for r_id in replace_id_list:
                if r_id != talking_id:
                    replace_id = r_id
                    break
            current_talk["to_id"] = replace_id
            logger.info(
                f"User {state['userid']} doesn't want to talk to the same person in such short time."
            )
            logger.info(
                f"User {state['userid']}: new player to talk {current_talk['to_id']}."
            )

    # only go through the following process when the conversation is checked to be necessary
    # get target name
    userid = current_talk["to_id"]
    character_data = {"characterId": userid}
    profile = make_api_request_sync("GET", "/characters/", params=character_data)
    if not profile["data"]:
        target_name = ""
        logger.warning(
            f"User {state['userid']} talking with an unknown character {current_talk['to_id']}"
        )
    else:
        target_name = profile["data"][0]["characterName"]
        target_profile = profile["data"][0]["full_profile"]
        logger.info(
            f"User {current_talk['to_id']} current state is {target_profile}."
        )

    # get self name
    my_name = state["character_stats"]["characterName"]

    # get topic
    topic_data = {
        "from_characterName": my_name,
        "to_characterName": target_name
    }
    topic_response = make_api_request_sync("GET", "/dialog_topic/", params=topic_data)
    if topic_response["data"]:
        topic = topic_response["data"]["topic"]
        content_type = topic_response["data"]["category"]
    else:
        content_type = "game"
        topic = ""
        logger.warning(f"User {state['userid']} failed to fetch topic. Using backup topic...")

    # special pair
    if {state['userid'], current_talk['to_id']} == {616422, 804851}:
        information = "Background information: Yi is the mother of at least two of CZ’s three children, although she has denied that they are currently romantic partners."
        if topic:
            topic += information
        else:
            topic = information
        logger.info(f"Special background for User {state['userid']} and {current_talk['to_id']}: information.")
    elif not topic:
        topic = ""

    logger.info(f"User {state['userid']} current topic is: {content_type}-{topic}")

    if content_type == "game":  # topic about games
        # get character_arc: from
        arc_response = make_api_request_sync(
            "GET", "/character_arc/", params={"characterId": state["userid"], "k": 1}
        )
        if not arc_response["data"]:
            arc_data_from = []
        else:
            arc_data_from = arc_response["data"][0]
            arc_data_from.pop("created_at", None)
            arc_data_from.pop("characterId", None)
        logger.info(f"User {state['userid']} current character arc is {arc_data_from}")

        # get character_arc: to
        arc_response = make_api_request_sync(
            "GET", "/character_arc/", params={"characterId": current_talk['to_id'], "k": 1}
        )
        if not arc_response["data"]:
            arc_data_to = []
        else:
            arc_data_to = arc_response["data"][0]
            arc_data_to.pop("created_at", None)
            arc_data_to.pop("characterId", None)
        logger.info(f"User {current_talk['to_id']} current character arc is {arc_data_to}")

        # get impression:from
        impression_query_data = {
            "from_id": state["userid"],
            "to_id": current_talk["to_id"],
            "k": 1,
        }
        impression_response = make_api_request_sync(
            "GET", "/impressions/", params=impression_query_data
        )

        if impression_response["data"]:
            current_impression_from = impression_response["data"][0]
        else:
            current_impression_from = []
        logger.info(
            f"The current impression from User {state['userid']} to User {current_talk['to_id']} is {current_impression_from}"
        )

        # get impression:to
        impression_query_data = {
            "from_id": current_talk["to_id"],
            "to_id": state["userid"],
            "k": 1,
        }
        impression_response = make_api_request_sync(
            "GET", "/impressions/", params=impression_query_data
        )

        if impression_response["data"]:
            current_impression_to = impression_response["data"][0]
        else:
            current_impression_to = []
        logger.info(
            f"The current impression from User {current_talk['to_id']} to User {state['userid']} is {current_impression_to}"
        )

        # get self action
        get_action_log_params = {"characterId": state["userid"], "k": 5}
        action_response = make_api_request_sync(
            "GET", "/action_log/", params=get_action_log_params
        )
        if action_response["data"] is not None:
            action_data = action_response["data"]
            memory_from = {}
            for act in action_data:
                key = act["command"]
                value = act["description"]
                if key not in memory_from:
                    memory_from[key] = value
        else:
            memory_from = {}
        logger.info(f"User {state['userid']} current actions are: {memory_from}")

        # get target action
        get_action_log_params = {"characterId": current_talk["to_id"], "k": 5}
        action_response = make_api_request_sync(
            "GET", "/action_log/", params=get_action_log_params
        )
        if action_response["data"] is not None:
            action_data = action_response["data"]
            memory_to = {}
            for act in action_data:
                key = act["command"]
                value = act["description"]
                if key not in memory_to:
                    memory_to[key] = value
        else:
            memory_to = {}
        logger.info(f"User {current_talk['to_id']} current actions are: {memory_to}")

        payload = {
            "character_stats_from": memory_from,
            "character_stats_to": memory_to,
            "topic": topic,
            "impression_from": current_impression_from,
            "impression_to": current_impression_to,
            "target_name": target_name,
            "my_name": my_name,
            "personality_from": arc_data_from,
            "personality_to": arc_data_to
        }
        generator = conversation_generator
        generator_prompt = conversation_generator_prompt
    else:
        payload = {
            "type": content_type,
            "topic": topic,
            "from_name": my_name,
            "to_name": target_name,
        }
        generator = simple_content_generator
        generator_prompt = simple_content_prompt

    # generate conversation content
    retry_count = 0
    while retry_count < 3:
        try:
            conversation_content = generator.invoke(
                payload
            )
            full_prompt = generator_prompt.format(**payload)
            logger.info("======conversation_generator======\n" + full_prompt)

            # Reconstruct the format
            lines = conversation_content["content"].strip().split('\n')
            all_content = []
            for line in lines:
                key, value = line.split(':')
                all_content.append({key.strip(): value.strip()})
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in starting a conversation: {e}"
            )
            retry_count += 1
            continue

    logger.info(
        f"The conversation FROM {current_talk['from_id']} at GAME TIME {current_talk['start_time']} on topic {topic} has been generated."
    )
    logger.info(f"{all_content}")

    from_to_count = 0
    for sentence in all_content:
        current_realtime = datetime.now()
        current_day, current_hour, current_minute = calculate_game_time(
            current_realtime
        )
        send_gametime = [
            current_day,
            f"{current_hour:02}" + ":" + f"{current_minute:02}",
        ]
        send_realtime = f"{current_realtime.year}-{current_realtime.month}-{current_realtime.day} {current_realtime.hour}:{current_realtime.minute:02}"

        if from_to_count % 2 == 0:
            id1 = current_talk["from_id"]
            id2 = current_talk["to_id"]
        else:
            id2 = current_talk["from_id"]
            id1 = current_talk["to_id"]
        # store the message to database
        store_conversation_data = {
            "from_id": id1,
            "to_id": id2,
            "start_time": current_talk["start_time"],
            "start_day": current_day,
            "message": list(sentence.values())[0],
            "send_gametime": send_gametime,
            "send_realtime": send_realtime,
            "category": content_type,
            "topic": topic
        }
        store_response = make_api_request_sync(
            "POST", "/conversation/", data=store_conversation_data
        )
        logger.info(
            f"User {id1} conversation message stored: {store_response['message']}"
        )
        from_to_count += 1

    # update the daily_task list
    if len(state["daily_task"]) > 1:
        state["daily_task"] = state["daily_task"][1:]
    else:
        state["daily_task"] = []

    # handling finished conversation
    conversation_finished = {
        "characterIds": [current_talk["from_id"], current_talk["to_id"]],
        "dialogue": all_content,
        "start_time": current_talk["start_time"],
        "start_day": current_time[0],
    }
    await handling_finished_conversation(conversation_finished)

    return state


# Check whether all tasks are complete
def all_conversation_started(
    state: ConversationState,
) -> Literal["Conversation_starter", "__end__"]:
    if len(state["daily_task"]) == 0:
        logger.info(f"🧠 ALL CONVERSATIONS HAVE BEEN LAUNCHED.")
        return "__end__"
    else:
        logger.info(f"🧠 NEXT CONVERSATION WILL BE LAUNCHED...")
        return "Conversation_starter"


# handling the finished conversations
async def handling_finished_conversation(conversation):
    logger.info(
        f"Conversation between Users {conversation['characterIds']} started at {conversation['start_time']} is finished."
    )

    stored_impression = await update_impression(
        conversation["characterIds"][0],
        conversation["characterIds"][1],
        conversation["dialogue"],
    )
    updated_intimacy = await update_intimacy(
        conversation["characterIds"][0],
        conversation["characterIds"][1],
        conversation["dialogue"],
    )
    return stored_impression, updated_intimacy


async def update_impression(id1: int, id2: int, conversation):
    relation_list = """
        1.Have a crush,
        2.Secret crush,
        3.Simp,
        4.Partner,
        5.Lover,
        6.Stranger,
        7.Husband and wife / couple,
        8.Ex-wife / ex-husband,
        9.Nemesis,
        10.Benefactor,
        11.Idol,
        12.Mentor and apprentice,
        13.Relative, including Father, Mother, Son, Daughter, Grandfather, Grandmother, Grandson, Granddaughter
    """

    # get from_name
    character_data = {"characterId": id1}
    profile = make_api_request_sync("GET", "/characters/", params=character_data)
    if not profile["data"]:
        my_name = {}
    else:
        my_name = profile["data"][0]["characterName"]

    # get to_name
    character_data = {"characterId": id2}
    profile = make_api_request_sync("GET", "/characters/", params=character_data)
    if not profile["data"]:
        target_name = {}
    else:
        target_name = profile["data"][0]["characterName"]

    # update impression
    retry_count = 0
    while retry_count < 3:
        try:
            payload = {
                "conversation": conversation,
                "relation_list": relation_list,
                "from_name": my_name,
                "to_name": target_name,
            }
            impression = impression_update.invoke(
                payload
            )
            full_prompt = impression_update_prompt.format(**payload)
            logger.info("======impression_update======\n" + full_prompt)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {id1} and User {id2} Error in update impressions: {e}"
            )
            retry_count += 1
            continue

    logger.info(f"🧠 IMPRESSION FROM USER {id1} to USER {id2} UPDATED...")
    logger.info(impression.impression1)
    logger.info(f"🧠 IMPRESSION FROM USER {id2} to USER {id1} UPDATED...")
    logger.info(impression.impression2)

    # Insert impressions to database
    document1 = {"from_id": id1, "to_id": id2, "impression": impression.impression1}
    store_impression1_response = make_api_request_sync(
        "POST", "/impressions/", data=document1
    )
    logger.info(
        f"From User {id1} to User {id2}: {store_impression1_response['message']}."
    )

    document2 = {"from_id": id2, "to_id": id1, "impression": impression.impression2}
    store_impression2_response = make_api_request_sync(
        "POST", "/impressions/", data=document2
    )
    logger.info(
        f"From User {id2} to User {id1}: {store_impression2_response['message']}."
    )
    return {"new impressions": [impression.impression1, impression.impression2]}


# initialize conversation state when a ws connection is built for certain agent
def initialize_conversation_state(userid, websocket) -> ConversationState:
    # get profile
    character_data = {"characterId": userid}
    profile = make_api_request_sync("GET", "/characters/", params=character_data)
    if not profile["data"]:
        character_stats = {}
    else:
        character_stats = profile["data"][0]
    logger.info(f"User {userid}: {profile['message']}")
    logger.info(f"User {userid} current state is: {character_stats}")

    initial_prompt = {
        "topic_requirements": "",
        "impression_impact": {
            "Relation": "Relation influences the length of conversation and how much information from player profiles should be included.",
            "Emotion": "Emotion determines the tone of the players.",
            "Personlality": "Personality influence the length of each player's answer and their willingness towards conversation.",
            "Habits and preferences": "Habits and preferences are something that one player thinks the other could be interested in and can also be mentioned in the conversation.",
        },
    }
    state = ConversationState(
        userid=userid,
        character_stats=character_stats,
        ongoing_task=[],
        daily_task=[],
        message_queue=asyncio.Queue(),
        waiting_response=asyncio.Queue(),
        websocket=websocket,
        prompt=initial_prompt,
    )
    return state


# workflow for planning conversation tasks and starting conversations
def start_conversation_workflow():
    workflow = StateGraph(ConversationState)
    workflow.add_node("Conversation_planner", generate_daily_conversation_plan)
    workflow.add_node("Conversation_starter", start_conversation)
    workflow.set_entry_point("Conversation_planner")
    workflow.add_conditional_edges("Conversation_starter", all_conversation_started)
    workflow.add_edge("Conversation_planner", "Conversation_starter")
    return workflow.compile()


# update intimacy marks
async def update_intimacy(id1: int, id2: int, conversation):
    logger.info(f"🧠 MARKING THE CONVERSATION...")

    character_data = {"characterId": id1}
    profile_response_1 = make_api_request_sync("GET", "/characters/", params=character_data)
    if profile_response_1["data"]:
        profile1 = profile_response_1["data"][0]["full_profile"]
    else:
        profile1 = ""

    character_data = {"characterId": id2}
    profile_response_2 = make_api_request_sync("GET", "/characters/", params=character_data)
    if profile_response_2["data"]:
        profile2 = profile_response_2["data"][0]["full_profile"]
    else:
        profile2 = ""

    retry_count = 0
    while retry_count < 3:
        try:
            payload = {
                    "profile1": profile1,
                    "profile2": profile2,
                    "conversation": conversation,
            }
            intimacy_mark = conversation_intimacy_mark.invoke(
                payload
            )
            full_prompt = intimacy_mark_prompt.format(**payload)
            logger.info("======intimacy_mark======\n" + full_prompt)
            break
        except Exception as e:
            logger.error(
                f"⛔ User {id1} and User {id2} Error in updating intimacy score: {e}"
            )
            retry_count += 1
            continue

    logger.info(f"The conversation is {conversation}.")

    mark1 = mark_map(intimacy_mark.mark1)
    mark2 = mark_map(intimacy_mark.mark2)

    logger.info(
        f"User {id1}'s attitude towards the conversation is: {mark1}"
    )
    logger.info(
        f"User {id2}'s attitude towards the conversation is: {mark2}"
    )

    intimacy_query_data = {"from_id": id1, "to_id": id2}
    response = make_api_request_sync("GET", "/intimacy/", params=intimacy_query_data)
    if response["data"] is None:
        current_intimacy_1 = 50
        type_1 = "POST"
    else:
        type_1 = "PUT"
        current_intimacy_1 = response["data"][0]["intimacy_level"]

    intimacy_query_data = {"from_id": id2, "to_id": id1}
    response = make_api_request_sync("GET", "/intimacy/", params=intimacy_query_data)
    if response["data"] is None:
        current_intimacy_2 = 50
        type_2 = "POST"
    else:
        type_2 = "PUT"
        current_intimacy_2 = response["data"][0]["intimacy_level"]

    logger.info(
        f"Past intimacy mark from User {id1} to User {id2} is {current_intimacy_1}."
    )
    logger.info(
        f"Past intimacy mark from User {id2} to User {id1} is {current_intimacy_2}."
    )

    current_intimacy_1 += mark1
    current_intimacy_1 = min(current_intimacy_1, 100)
    current_intimacy_1 = max(current_intimacy_1, 0)
    current_intimacy_2 += mark2
    current_intimacy_2 = min(current_intimacy_2, 100)
    current_intimacy_2 = max(current_intimacy_2, 0)

    logger.info(
        f"New intimacy mark from User {id1} to User {id2} is {current_intimacy_1}."
    )
    logger.info(
        f"New intimacy mark from User {id2} to User {id1} is {current_intimacy_2}."
    )

    name = "intimacy_level"
    if type_1 == "PUT":
        name = "new_" + name
    update_intimacy_data = {"from_id": id1, "to_id": id2, name: current_intimacy_1}
    endpoint = "/intimacy/"
    response = make_api_request_sync(type_1, endpoint, data=update_intimacy_data)
    logger.info(f"From User {id1} to User {id2}: {response['message']}.")

    name = "intimacy_level"
    if type_2 == "PUT":
        name = "new_" + name
    update_intimacy_data = {"from_id": id2, "to_id": id1, name: current_intimacy_2}
    endpoint = "/intimacy/"
    response = make_api_request_sync(type_2, endpoint, data=update_intimacy_data)
    logger.info(f"From User {id2} to User {id1}: {response['message']}.")


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
    # sorted_numbers[0] = 1

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
