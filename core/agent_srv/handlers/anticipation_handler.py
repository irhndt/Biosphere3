from .base_handler import BaseHandler
from core.agent_srv.prompts import *
from core.agent_srv.utils import *
from core.db.api_client import agent_api, game_api
from loguru import logger


class AnticipationHandler(BaseHandler):
    """
    Handler for check and refine ActionList
    Refering to the current state of the agent, the handler will check the ActionList and refine it.
    """
