from core.conversation_srv.api_utils import make_api_request_sync, conversation_intimacy_mark
from loguru import logger
from core.conversation_srv.conversation_model import ConversationState, ConversationTask
from core.conversation_srv.conversation_prompts import intimacy_mark_prompt


# map the raw marks
def mark_map(x: int):
    mapping = {
        5: 8,
        4: 4,
        3: 0,
        2: -3,
        1: -5
    }
    return mapping.get(x, 0)


# update intimacy marks
async def update_intimacy(state: ConversationState, current_talk: ConversationTask, conversation):
    logger.info(f"🧠 MARKING THE CONVERSATION...")
    logger.info(f"The conversation is {conversation}.")

    # load ids
    id1 = current_talk["from_id"]
    id2 = current_talk["to_id"]

    # Get profiles
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

    # Get old intimacy marks
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

    # Generate new intimacy marks
    retry_count = 0
    intimacy_mark = ""
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

    if intimacy_mark != "":
        mark1 = mark_map(intimacy_mark.mark1)
        mark2 = mark_map(intimacy_mark.mark2)
    else:
        mark1 = 0
        mark2 = 0

    logger.info(
        f"User {id1}'s attitude towards the conversation is: {mark1}"
    )
    logger.info(
        f"User {id2}'s attitude towards the conversation is: {mark2}"
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
    if response["message"]:
        logger.info(f"From User {id1} to User {id2}: {response['message']}.")
    else:
        logger.warning(f"From User {id1} to User {id2}: failed to update intimacy mark.")

    name = "intimacy_level"
    if type_2 == "PUT":
        name = "new_" + name
    update_intimacy_data = {"from_id": id2, "to_id": id1, name: current_intimacy_2}
    endpoint = "/intimacy/"
    response = make_api_request_sync(type_2, endpoint, data=update_intimacy_data)
    if response["message"]:
        logger.info(f"From User {id2} to User {id1}: {response['message']}.")
    else:
        logger.warning(f"From User {id2} to User {id1}: failed to update intimacy mark.")

