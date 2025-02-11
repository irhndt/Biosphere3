from .base_handler import BaseHandler
from core.agent_srv.prompts import *
from core.agent_srv.utils import *
from core.db.api_client import agent_api, game_api
from loguru import logger
from core.agent_srv.action_rules import rules
from core.agent_srv.node_model import RefinedActionsAndState
from core.agent_srv.prompts import action_refiner_prompt


class AnticipationHandler(BaseHandler):
    """
    Handler for check and refine ActionList
    Refering to the current state of the agent, the handler will check the ActionList and refine it.
    """

    def __init__(self, model_name):
        super(BaseHandler, self).__init__()
        self.rules = rules
        self.action_refiner = self.create_planner(
            action_refiner_prompt,
            model_name,
            RefinedActionsAndState,
            0.5,
        )

    def process_action_list(self, action_list, current_state):
        """
        Process the action list and refine it.
        Args:
            action_list: list of actions
            current_state: current state of the agent
        Returns:
            refined action list
        """
        running_state = copy.copy(current_state)
        final_actions = []
        for action in action_list:
            current_action_list = copy.copy(final_actions)
            running_state, actions = self.refine_action(
                action, running_state, current_action_list
            )
            final_actions.extend(actions)

        # final_actions = self.final_check(final_actions, running_state)
        return final_actions

    def refine_action(self, action, current_state, current_action_list):
        """
        Refine the action based on the current state of the agent
        Args:
            action: action to be refined
            current_state: current state of the agent
        Returns:
            refined action
        """
        action_name = action.split(" ")[0]
        action_rule = self.rules[action_name]
        payload = {
            "action": action,
            "current_action_list": current_action_list,
            "current_state": current_state,
            "action_rule": action_rule,
        }
        refined_action_and_state = self.api_retry(
            self.action_refiner,
            payload,
            current_state,
            RefinedActionsAndState,
        )
        return refined_action_and_state.current_state, refined_action_and_state.actions
