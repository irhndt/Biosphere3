from datetime import datetime
import asyncio
from core.conversation_srv.conversation_model import ConversationState
from loguru import logger


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


async def sleep_with_connection(seconds: int, state:ConversationState):
    start_time = datetime.now()
    while True:
        current_time = datetime.now()
        time_difference = current_time - start_time
        seconds_difference = int(time_difference.total_seconds())
        if seconds_difference + 30 > seconds:
            seconds = seconds - seconds_difference
            await asyncio.sleep(seconds)
            return check_connection_state(state)
        else:
            connected = check_connection_state(state)
            if connected:
                await asyncio.sleep(30)
            else:
                return connected


def check_connection_state(state: ConversationState):
    if state["websocket"] is None or state["websocket"].closed:
        logger.error(f"⛔ User {state['userid']} websocket connection closed.")
        if state["daily_task"]:
            state["daily_task"] = []
            logger.warning(f"🧹 CLEAN UP RUNNING CONVERSATION TASKS FOR USER {state['userid']}.")
        return False
    else:
        return True