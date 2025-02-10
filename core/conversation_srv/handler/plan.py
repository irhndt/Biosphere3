from core.conversation_srv.api_utils import make_api_request_sync
from core.conversation_srv.conversation_model import ConversationState, DailyConversationPlan, ConversationTask
from loguru import logger
import random
from datetime import datetime
from core.conversation_srv.handler.clock import calculate_game_time


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


# check the talked volume of certain user to avoid too many conversations due to workflow restart
def check_daily_conversation_volume(id: int):
    day, hour, minute = calculate_game_time(datetime.now())
    volume_data = {
        "to_id": id,
        "start_day": day
    }
    volume_response = make_api_request_sync(
        "GET", "/conversation/", params=volume_data
    )
    if isinstance(volume_response["data"], list):
        start_time_collection = []
        for talk in volume_response["data"]:
            if talk["start_time"] not in start_time_collection:
                start_time_collection.append(talk["start_time"])
        return len(start_time_collection)
    else:
        return 0


# conversation planner
def a_plan(state: ConversationState):
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

    # check talked data, avoid too much talk every day
    talked_volume = check_daily_conversation_volume(state["userid"])
    if (ie == "Extraversion" and talked_volume >= 10) or (ie == "Introversion" and talked_volume >= 6):
        logger.info(f"Today User {state['userid']} has already talked for {talked_volume} times. Stop socializing.")
        return state
    else:
        conversation_number = max(1, conversation_number - talked_volume // 2)

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
    # target_list[0] = 612456#test
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

    return state
