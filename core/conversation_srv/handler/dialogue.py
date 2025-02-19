from core.conversation_srv.handler.clock import calculate_game_time
from core.conversation_srv.conversation_model import ConversationState, ConversationTask
from core.conversation_srv.api_utils import make_api_request_sync, conversation_generator, simple_content_generator
from core.conversation_srv.conversation_prompts import conversation_generator_prompt, simple_content_prompt
from core.conversation_srv.handler.plan import random_conversation_target
from core.conversation_srv.handler.information import load_all_information
from loguru import logger
from datetime import datetime


def change_conversation_target(state: ConversationState, current_talk: ConversationTask):
    # ensure that this target is not the one whom the agent is talking with
    current_time = calculate_game_time(datetime.now())
    talking_data = {
        "to_id": state["userid"],
        "start_day": current_time[0]
    }
    talking_response = make_api_request_sync(
        "GET", "/conversation/", params=talking_data
    )
    if isinstance(talking_response["data"], list) and talking_response["data"]:
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
    return state, current_talk


def load_generator(state: ConversationState, current_talk: ConversationTask):
    info = load_all_information(state, current_talk)

    if info.content_type == "game":  # topic about games
        payload = {
            "type": info.content_type,
            "topic": info.topic,
            "target_name": info.target_name,
            "my_name": info.my_name,
            "character_stats_from": info.memory_from,
            "character_stats_to": info.memory_to,
            "impression_from": info.current_impression_from,
            "impression_to": info.current_impression_to,
            "personality_from": info.arc_data_from,
            "personality_to": info.arc_data_to
        }
        generator = conversation_generator
        generator_prompt = conversation_generator_prompt
    else:
        payload = {
            "type": info.content_type,
            "topic": info.topic,
            "my_name": info.my_name,
            "target_name": info.target_name,
            "relation_from": info.relation_from,
            "relation_to": info.relation_to
        }
        generator = simple_content_generator
        generator_prompt = simple_content_prompt
    return generator, generator_prompt, payload


def reformat_conversation(raw_conversation: str, my_name: str, target_name: str):
    lines = raw_conversation.strip().split('\n')
    content = []
    for line in lines:
        if line:
            items = line.split(':')
            if len(items) == 2:
                content.append({items[0].strip(): items[1].strip()})
            else:
                current_name = my_name
                other_name = target_name
                for item in items:
                    if item == current_name:
                        continue
                    elif current_name in item or item == other_name:
                        exchange_name = current_name
                        current_name = other_name
                        other_name = exchange_name
                    content.append({current_name: item.split(other_name)[0]})
                    exchange_name = current_name
                    current_name = other_name
                    other_name = exchange_name
    return content


def save_conversation(all_content: list, current_talk: ConversationTask, content_type: str, topic: str):
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
        if store_response["message"]:
            logger.info(
                f"User {id1} conversation message stored: {store_response['message']}"
            )
        else:
            logger.warning(f"User {id1} failed to store conversation message.")
        from_to_count += 1


async def a_talk(state:ConversationState, current_talk: ConversationTask):
    # check to avoid repeat talk
    state, current_talk = change_conversation_target(state, current_talk)

    # load information and generator
    generator, generator_prompt, payload = load_generator(state, current_talk)

    # generate conversation content
    retry_count = 0
    all_content = ""
    while retry_count < 3:
        try:
            conversation_content = generator.invoke(
                payload
            )
            full_prompt = generator_prompt.format(**payload)
            logger.info("======conversation_generator======\n" + full_prompt)

            # Reconstruct the format
            all_content = reformat_conversation(conversation_content["content"], payload["my_name"], payload["target_name"])
            break
        except Exception as e:
            logger.error(
                f"⛔ User {state['userid']} Error in starting a conversation: {e}"
            )
            retry_count += 1
            continue

    if all_content != "":
        logger.info(
            f"The conversation FROM {current_talk['from_id']} at GAME TIME {current_talk['start_time']} has been generated."
        )
        logger.info(f"{all_content}")
    else:
        logger.error(f"⛔ User {state['userid']} failed to generate conversation content.")

    save_conversation(all_content, current_talk, payload["type"], payload["topic"])

    return state, all_content





