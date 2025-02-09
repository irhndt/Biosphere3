from core.conversation_srv.api_utils import make_api_request_sync, impression_update
from loguru import logger
from core.conversation_srv.conversation_model import ConversationTask, ConversationState
from core.conversation_srv.conversation_prompts import impression_update_prompt
from core.conversation_srv.handler.information import load_all_information

async def update_impression(state: ConversationState, current_talk: ConversationTask, conversation: list):
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

    id1 = current_talk["from_id"]
    id2 = current_talk["to_id"]

    # load information
    info = load_all_information(state, current_talk, "impression")

    # update impression: from->to
    retry_count = 0
    impression1 = ""
    while retry_count < 3:
        try:
            payload = {
                "conversation": conversation,
                "relation_list": relation_list,
                "relation_from": info.relation_from,
                "from_name": info.my_name,
                "to_name": info.target_name,
            }
            impression1 = impression_update.invoke(
                payload
            )
            full_prompt = impression_update_prompt.format(**payload)
            logger.info("======impression_update======\n" + full_prompt)
            break
        except Exception as e:
            logger.error(
                f"⛔ Error in update impressions from User {id1} to User {id2}: {e}"
            )
            retry_count += 1
            continue

    if impression1 != "":
        logger.info(f"🧠 IMPRESSION FROM USER {id1} to USER {id2} UPDATED...")
        logger.info(impression1.impression)
    else:
        impression1 = info.current_impression_from
        logger.warning(f"⛔ Impression from User {id1} to User {id2} failed to update. Keep using the old one.")

    # update impression: to->from
    retry_count = 0
    impression2 = ""
    while retry_count < 3:
        try:
            payload = {
                "conversation": conversation,
                "relation_list": relation_list,
                "relation_from": info.relation_to,
                "from_name": info.target_name,
                "to_name": info.my_name,
            }
            impression2 = impression_update.invoke(
                payload
            )
            full_prompt = impression_update_prompt.format(**payload)
            logger.info("======impression_update======\n" + full_prompt)
            break
        except Exception as e:
            logger.error(
                f"⛔ Error in update impressions from User {id2} to User {id1}: {e}"
            )
            retry_count += 1
            continue

    if impression2 != "":
        logger.info(f"🧠 IMPRESSION FROM USER {id2} to USER {id1} UPDATED...")
        logger.info(impression2.impression)
    else:
        impression2 = info.current_impression_to
        logger.warning(f"⛔ Impression from User {id2} to User {id1} failed to update. Keep using the old one.")

    # Insert impressions to database
    document1 = {"from_id": id1, "to_id": id2, "impression": impression1.impression}
    store_impression1_response = make_api_request_sync(
        "POST", "/impressions/", data=document1
    )
    if store_impression1_response["message"]:
        logger.info(
            f"From User {id1} to User {id2}: {store_impression1_response['message']}."
        )
    else:
        logger.warning(f"From User {id1} to User {id2}: failed to store new impression.")

    document2 = {"from_id": id2, "to_id": id1, "impression": impression2.impression}
    store_impression2_response = make_api_request_sync(
        "POST", "/impressions/", data=document2
    )
    if store_impression2_response["message"]:
        logger.info(
            f"From User {id2} to User {id1}: {store_impression2_response['message']}."
        )
    else:
        logger.warning(f"From User {id2} to {id1}: failed to store new impression.")

    return {"new impressions": [impression1, impression2]}