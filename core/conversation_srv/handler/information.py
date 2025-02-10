from core.conversation_srv.conversation_model import ConversationState, ConversationTask, DialogueInformation
from core.conversation_srv.api_utils import make_api_request_sync
from loguru import logger


def load_all_information(state: ConversationState, current_talk: ConversationTask, mod: str = "dialogue"):
    # load all information from db; in order to save timee and resources, mod="impression" will load less info
    if mod == "impression":
        target_name, my_name = load_names(state, current_talk)
        current_impression_from, current_impression_to, relation_from, relation_to = load_impression(state, current_talk)
        content_type = ''
        topic = ''
        memory_from = {}
        memory_to = {}
        arc_data_from = {}
        arc_data_to = {}
    else:
        target_name, my_name = load_names(state, current_talk)
        content_type, topic = load_topic(state, current_talk, my_name, target_name)
        current_impression_from, current_impression_to, relation_from, relation_to = load_impression(state, current_talk)
        memory_from, memory_to = load_action(state, current_talk)
        arc_data_from, arc_data_to = load_arc(state, current_talk)

    info = DialogueInformation(
        content_type=content_type,
        topic=topic,
        target_name=target_name,
        my_name=my_name,
        memory_from=memory_from,
        memory_to=memory_to,
        current_impression_from=current_impression_from,
        current_impression_to=current_impression_to,
        relation_from=relation_from,
        relation_to=relation_to,
        arc_data_from=arc_data_from,
        arc_data_to=arc_data_to,
    )

    return info


def load_topic(state: ConversationState, current_talk: ConversationTask, my_name, target_name):
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
        logger.warning(f"User {state['userid']} failed to fetch topic. Using default topic {content_type}.")

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
    return content_type, topic


def load_names(state: ConversationState, current_talk: ConversationTask):
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

    return target_name, my_name


def load_action(state: ConversationState, current_talk: ConversationTask):
    # get self action
    get_action_log_params = {"characterId": state["userid"], "k": 5}
    action_response = make_api_request_sync(
        "GET", "/action_log/", params=get_action_log_params
    )
    if action_response["data"]["log"] is not None:
        action_data = action_response["data"]["log"]
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
    if action_response["data"]["log"] is not None:
        action_data = action_response["data"]["log"]
        memory_to = {}
        for act in action_data:
            key = act["command"]
            value = act["description"]
            if key not in memory_to:
                memory_to[key] = value
    else:
        memory_to = {}
    logger.info(f"User {current_talk['to_id']} current actions are: {memory_to}")

    return memory_from, memory_to


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


def load_impression(state: ConversationState, current_talk: ConversationTask):
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

    # strip relation
    relation_from = strip_relation(current_impression_from)
    relation_to = strip_relation(current_impression_to)

    return current_impression_from, current_impression_to, relation_from, relation_to


def load_arc(state: ConversationState, current_talk: ConversationTask):
    # get character_arc: from
    arc_response = make_api_request_sync(
        "GET", "/character_arc/", params={"characterId": state["userid"], "k": 1}
    )
    if not arc_response["data"]:
        arc_data_from = {}
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
        arc_data_to = {}
    else:
        arc_data_to = arc_response["data"][0]
        arc_data_to.pop("created_at", None)
        arc_data_to.pop("characterId", None)
    logger.info(f"User {current_talk['to_id']} current character arc is {arc_data_to}")

    return arc_data_from, arc_data_to


