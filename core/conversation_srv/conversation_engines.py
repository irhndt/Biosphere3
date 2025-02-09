from core.conversation_srv.api_utils import *
from loguru import logger
from typing import Literal
import websockets
import json
from core.conversation_srv.handler.plan import a_plan
from core.conversation_srv.handler.dialogue import a_talk
from core.conversation_srv.handler.clock import calculate_game_time, sleep_with_connection
from core.conversation_srv.handler.impression import update_impression
from core.conversation_srv.handler.intimacy import update_intimacy
from datetime import datetime
import random
from langgraph.graph import StateGraph

logger.add(
    "conversation_engines.log",
    format="{time} {level} {message}",
)


# initialize conversation state when a ws connection is built for certain agent
def initialize_conversation_state(userid, websocket) -> ConversationState:
    # get profile
    character_data = {"characterId": userid}
    profile = make_api_request_sync("GET", "/characters/", params=character_data)
    if not profile["message"]:
        character_stats = {}
        logger.error(f"⛔ Error in initializing conversation instance: fail to fetch profile.")
    elif not profile["data"]:
        character_stats = {}
        logger.error(f"⛔ Error in initializing conversation instance: {profile['message']}.")
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


async def generate_daily_conversation_plan(state: ConversationState):
    # reset the task list
    state["daily_task"] = []

    # update profile
    userid = state["userid"]
    character_data = {"characterId": userid}
    profile = make_api_request_sync(
        "GET", "/characters/", params=character_data
    )
    if not profile["message"]:
        logger.error(f"⛔ User {state['userid']} failed to fetch profile.")
    if not profile["data"]:
        state["character_stats"] = {}
    else:
        state["character_stats"] = profile["data"][0]
    logger.info(f"User {state['userid']}: {profile['message']}")
    logger.info(f"User {state['userid']} current state is: {state['character_stats']}")

    # generate conversation plan
    state = a_plan(state)

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
        sleep_connected = await sleep_with_connection(sleep_time, state)
        if not sleep_connected:
            return state
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
        logger.warning(f"User {state['userid']} failed to fetch profile. Run the workflow with old profile.")
    else:
        state["character_stats"] = profile["data"][0]
    logger.info(f"User {state['userid']} current state is: {state['character_stats']}")

    # generate dialogue
    state, all_content = a_talk(state, current_talk)

    # update the daily_task list
    if len(state["daily_task"]) > 1:
        state["daily_task"] = state["daily_task"][1:]
    else:
        state["daily_task"] = []

    # handling finished conversation
    conversation_finished = {
        "current_talk": current_talk,
        "dialogue": all_content,
    }
    await handling_finished_conversation(state, conversation_finished)

    return state


# handling the finished conversations
async def handling_finished_conversation(state, conversation):
    logger.info(
        f"Conversation between Users {conversation['characterIds']} started at {conversation['start_time']} is finished."
    )

    stored_impression = await update_impression(
        state,
        conversation["current_talk"],
        conversation["dialogue"],
    )
    updated_intimacy = await update_intimacy(
        state,
        conversation["current_talk"],
        conversation["dialogue"],
    )
    return stored_impression, updated_intimacy


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


# workflow for planning conversation tasks and starting conversations
def start_conversation_workflow():
    workflow = StateGraph(ConversationState)
    workflow.add_node("Conversation_planner", generate_daily_conversation_plan)
    workflow.add_node("Conversation_starter", start_conversation)
    workflow.set_entry_point("Conversation_planner")
    workflow.add_conditional_edges("Conversation_starter", all_conversation_started)
    workflow.add_edge("Conversation_planner", "Conversation_starter")
    return workflow.compile()

