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

    # get new daily objectives
    get_daily_objectives_data = {"characterId": state["userid"], "count": 5}
    objective_response = make_api_request_sync(
        "GET", "/decision/", params=get_daily_objectives_data
    )
    if objective_response["data"] is not None:
        memory = objective_response["data"]
    else:
        memory = []
    logger.info(f"User {state['userid']} current daily objectives are: {memory}")

    # get character_arc
    arc_response = make_api_request_sync(
        "GET", "/character_arc/", params={"characterId": state["userid"], "k": 1}
    )
    if not arc_response["data"]:
        arc_data = []
    else:
        arc_data = arc_response["data"]
    logger.info(f"User {state['userid']} current character arc is {arc_data}")

    # get featured prompt (topic)
    topic_response = make_api_request_sync(
        "GET", "/conversation_prompt/", params={"characterId": state["userid"]}
    )
    if not topic_response["data"]:
        topic_requirement = ""
    else:
        topic_requirement = topic_response["data"][0]["topic_requirements"]

    # look up the past conversation topics
    current_day, current_hour, current_minute = calculate_game_time(datetime.now())
    get_conversation_memory_params = {
        "characterId": state["userid"],
        "day": current_day - 1,
    }
    past_topic_response = make_api_request_sync(
        "GET", "/conversation_memory/", params=get_conversation_memory_params
    )
    if not past_topic_response["data"]:
        past_topics = []
    else:
        past_topics = past_topic_response["data"][0]["topic_plan"]

    # generate conversation time list
    start_time_list = []
    conversation_number = random.randint(10, 15)  # total number of conversations
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
    logger.info(
        f"User {state['userid']} planned to have conversation with {target_list}."
    )

    # generate conversation topics list.
    style_type = [
        {"positive"},
        {"negative"}
    ]
    topic_list = []
    for target in target_list:
        retry_count = 0
        while retry_count < 3:
            try:
                character_data = {"characterId": target}
                target_response = make_api_request_sync(
                    "GET", "/characters/", params=character_data
                )
                if target_response["data"]:
                    target_profile = target_response["data"][0]
                else:
                    target_profile = {}

                style_select = random.randint(1, 10)  # select topic style
                if style_select > 7:
                    style = style_type[1]
                else:
                    style = style_type[0]

                current_topic = conversation_topic_planner.invoke(
                    {
                        "character_stats": state["character_stats"],
                        "memory": memory,
                        "personality": arc_data,
                        "target_profile": target_profile,
                        "style": style,
                        "topic_list": topic_list,
                        "past_topics": past_topics,
                        "topic_requirements": topic_requirement
                    }
                )
                logger.info(
                    f"User {state['userid']} planned to talk with User {target} about {current_topic['topics']}."
                )
                topic_list.append(current_topic["topics"])
                break
            except Exception as e:
                logger.error(
                    f"⛔ User {state['userid']} Error in generate daily conversation topics: {e}"
                )
                retry_count += 1
                continue
    logger.info(
        f"Today User {state['userid']} is going to talk with others about: {topic_list}"
    )

    conversation_plan = DailyConversationPlan(conversations=[])

    if start_time_list:
        for index, start_time in enumerate(start_time_list):
            talk = topic_list[index]
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

        # update daily conversation plan to database
        current_day, current_hour, current_minute = calculate_game_time(datetime.now())
        get_conversation_memory_params = {
            "characterId": state["userid"],
            "day": current_day,
        }
        memory_response = make_api_request_sync(
            "GET", "/conversation_memory/", params=get_conversation_memory_params
        )
        if not memory_response["data"]:
            store_conversation_memory_data = {
                "characterId": state["userid"],
                "day": current_day,
                "topic_plan": topic_list,
                "time_list": start_time_list,
                "started": [],
            }
            memory_store_response = make_api_request_sync(
                "POST", "/conversation_memory/", data=store_conversation_memory_data
            )
            logger.info(
                f"User {state['userid']} conversation plan stored: {memory_store_response['message']}"
            )
        else:
            old_topic = memory_response["data"][0]["topic_plan"]
            old_time = memory_response["data"][0]["time_list"]
            if not memory_response["data"][0]["started"]:
                point = 0
            else:
                point = len(memory_response["data"][0]["started"])
            update_conversation_memory_data = {
                "characterId": state["userid"],
                "day": current_day,
                "update_fields": {
                    "topic_plan": old_topic[0: point] + topic_list,
                    "time_list": old_time[0: point] + start_time_list,
                },
            }
            memory_update_response = make_api_request_sync(
                "PUT", "/conversation_memory/", data=update_conversation_memory_data
            )
            logger.info(
                f"User {state['userid']} conversation plan updated: {memory_update_response['message']}"
            )

        logger.info(f"🧠 NEW CONVERSATION PLAN GENERATED...")
        logger.info(
            f"New conversation plan of User {state['userid']}: {state['daily_task']}"
        )
    return state


def create_message(
    character_id, message_name, conversation: RunningConversation, message_code=100
):  # messagecode=100 for conversation system
    return {
        "characterId": character_id,
        "messageCode": message_code,
        "messageName": message_name,
        "data": conversation,
    }


# send message through ws
async def send_conversation_message(
    state: ConversationState, conversation: RunningConversation
):
    websocket = state["websocket"]
    if websocket is None or websocket.closed:
        logger.error(f"⛔ User {state['userid']}: WebSocket is not connected.")
        return
    try:
        message = create_message(
            character_id=state["userid"],
            message_name="to_agent",
            conversation=conversation,
        )
        await websocket.send(json.dumps(message))
        logger.info(f"📤 User {state['userid']}: Sent a response message: {message}")
    except websockets.ConnectionClosed:
        logger.warning(
            f"User {state['userid']}: WebSocket connection closed during send."
        )
    except Exception as e:
        logger.error(f"User {state['userid']}: Error sending message: {e}")


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
        talking_id = talking_conversation["to_id"]
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

    # get conversations that have already happened with target
    talked_data = {
        "from_id": current_talk["to_id"],
        "to_id": state["userid"],
        "start_day": current_time[0]
    }
    talked_response = make_api_request_sync(
        "GET", "/conversation/", params=talked_data
    )

    logger.info(f"🧠 CHECKING WHETHER TO START THE CONVERSATION ...")
    need_start = True
    if talked_response["data"]:
        logger.info(
            f"User {state['userid']} has talked with {current_talk['to_id']} today."
        )
        logger.info(
            f"Conversation data: {talked_response['data']}."
        )
        # check whether to start this task
        retry_count = 0
        while retry_count < 3:
            try:
                check_response = conversation_check.invoke(
                    {
                        "profile": state["character_stats"],
                        "current_talk": current_talk,
                        "finished_talk": talked_response["data"],
                    }
                )
                break
            except Exception as e:
                logger.error(f"⛔ User {state['userid']} Error in check conversation: {e}")
                retry_count += 1
                continue
        need_start = check_response["Need"]

    logger.info(
        f"User {state['userid']} final decision on whether to start the conversation is: {need_start}."
    )

    # only go through the following process when the conversation is checked to be necessary
    if need_start:
        # get character_arc: from
        arc_response = make_api_request_sync(
            "GET", "/character_arc/", params={"characterId": state["userid"], "k": 1}
        )
        if not arc_response["data"]:
            arc_data_from = []
        else:
            arc_data_from = arc_response["data"]
        logger.info(f"User {state['userid']} current character arc is {arc_data_from}")

        # get character_arc: to
        arc_response = make_api_request_sync(
            "GET", "/character_arc/", params={"characterId": current_talk['to_id'], "k": 1}
        )
        if not arc_response["data"]:
            arc_data_to = []
        else:
            arc_data_to = arc_response["data"]
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

        # get target name
        userid = current_talk["to_id"]
        character_data = {"characterId": userid}
        profile = make_api_request_sync("GET", "/characters/", params=character_data)
        if not profile["data"]:
            target_name = ""
            target_profile = {}
            style_to = ""
            logger.warning(
                f"User {state['userid']} talking with an unknown character {current_talk['to_id']}"
            )
        else:
            target_name = profile["data"][0]["characterName"]
            target_profile = profile["data"][0]
            style_to = profile["data"][0]["characterName"]
            logger.info(
                f"User {current_talk['to_id']} current state is {target_profile}."
            )

        # get self name
        my_name = state["character_stats"]["characterName"]
        style_from = state["character_stats"]["language_style"]

        # generate conversation content
        retry_count = 0
        while retry_count < 3:
            try:
                conversation_content = conversation_generator.invoke(
                    {
                        "character_stats_from": state["character_stats"],
                        "character_stats_to": target_profile,
                        "topic": current_talk["topic"],
                        "impression_from": current_impression_from,
                        "impression_to": current_impression_to,
                        "target_name": target_name,
                        "my_name": my_name,
                        "personality_from": arc_data_from,
                        "personality_to": arc_data_to,
                        "style_from": style_from,
                        "style_to": style_to,
                        "impact": state["prompt"]["impression_impact"]
                    }
                )

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
            f"The conversation FROM {current_talk['from_id']} at GAME TIME {current_talk['start_time']} on topic {current_talk['topic']} has been generated."
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
            }
            store_response = make_api_request_sync(
                "POST", "/conversation/", data=store_conversation_data
            )
            logger.info(
                f"User {id1} conversation message stored: {store_response['message']}"
            )
            from_to_count += 1

        # update the daily conversation plan
        add_started_data = {
            "characterId": state["userid"],
            "day": current_time[0],
            "add_started": {
                "time": current_talk["start_time"],
                "topic": current_talk["topic"],
            },
        }
        start_add_response = make_api_request_sync(
            "PUT", "/conversation_memory/", data=add_started_data
        )
        logger.info(
            f"User {state['userid']} conversation memory added: {start_add_response['message']}"
        )
    else:
        logger.info(
            f"The conversation FROM {current_talk['from_id']} at GAME TIME {current_talk['start_time']} on topic {current_talk['topic']} is canceled after check."
        )

    # update the daily_task list
    if len(state["daily_task"]) > 1:
        state["daily_task"] = state["daily_task"][1:]
    else:
        state["daily_task"] = []

    # handling finished conversation
    if need_start:
        # Record finished conversation
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

    # update impression
    retry_count = 0
    while retry_count < 3:
        try:
            impression = impression_update.invoke(
                {"conversation": conversation, "relation_list": relation_list}
            )
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
    profile1 = make_api_request_sync("GET", "/characters/", data=character_data)

    character_data = {"characterId": id2}
    profile2 = make_api_request_sync("GET", "/characters/", data=character_data)

    retry_count = 0
    while retry_count < 3:
        try:
            intimacy_mark = conversation_intimacy_mark.invoke(
                {
                    "profile1": profile1,
                    "profile2": profile2,
                    "conversation": conversation,
                }
            )
            break
        except Exception as e:
            logger.error(
                f"⛔ User {id1} and User {id2} Error in updating intimacy score: {e}"
            )
            retry_count += 1
            continue

    logger.info(f"The conversation is {conversation}.")
    logger.info(
        f"User {id1}'s attitude towards the conversation is: {intimacy_mark.mark1 - 3}"
    )
    logger.info(
        f"User {id2}'s attitude towards the conversation is: {intimacy_mark.mark2 - 3}"
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

    current_intimacy_1 += intimacy_mark.mark1 - 3
    current_intimacy_1 = min(current_intimacy_1, 100)
    current_intimacy_1 = max(current_intimacy_1, 0)
    current_intimacy_2 += intimacy_mark.mark2 - 3
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
def calculate_game_time(real_time=datetime.now(), day1_str="2024-7-1 0:00"):
    day1 = datetime.strptime(day1_str, "%Y-%m-%d %H:%M")
    elapsed_time = real_time - day1
    game_elapsed_time = elapsed_time * 7
    game_day = game_elapsed_time.days
    total_seconds = int(game_elapsed_time.total_seconds())
    remaining_seconds = total_seconds - (game_day * 86400)
    game_hour, remainder = divmod(remaining_seconds, 3600)
    game_minute, seconds = divmod(remainder, 60)
    return [game_day, game_hour, game_minute]


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
    # sorted_numbers[0] = 5

    for t in sorted_numbers:
        add_hour, add_minute = divmod(minute + t, 60)
        if (hour + add_hour) >= 24:
            break
        elif (hour + add_hour) == 23 and add_minute >= 40:
            break
        start_time = f"{(hour+add_hour):02}" + ":" + f"{add_minute:02}"
        time_list.append(start_time)

    return time_list

