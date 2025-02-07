from core.agent_srv.node_model import RunningState
from core.agent_srv.handlers import *
from loguru import logger


class MainTest:
    def __init__(self):
        self.planner = PlanningHandler()
        self.career_cv = CareerCVHandler()
        self.accommodation = AccommodationHandler()
        self.reflection = ReflectionHandler()

    async def test_plan(self, state):
        await self.planner.generate_daily_objective(state)
        await self.planner.generate_crafting_and_trading_sequence(state)

    async def test_cv(self, state):
        await self.career_cv.generate_cv(state)

    async def test_accommodation(self, state):
        await self.accommodation.generate_accommodation_decision(state)

    async def test_reflection(self, state):
        await self.reflection.generate_reflection(state)


if __name__ == "__main__":
    import asyncio
    import core.agent_srv.utils as utils

    # import pprint
    async def test_put_false_action_info(state: RunningState):
        false_action_info = {
            "actionName": "goto forest",
            "msg": "No location named 'forest'.",
        }
        state["false_action_queue"].put_nowait(false_action_info)
        state["decision"]["detailed_meta_seq"] = [
            {
                "action": "goto forest",
                "cost": None,
                "inventory_after": None,
                "inventory_before": None,
                "reason": "Move to the forest to gather wood.",
                "status_after": None,
                "status_before": None,
            },
            {
                "action": "craft wood 10",
                "cost": "50 energy total (5 energy per item × 10)",
                "inventory_after": "Later inventory is {wood: 10}",
                "inventory_before": "Current inventory is {}",
                "reason": "Gather wood to prepare for crafting wooden_boards.",
                "status_after": "Later energy is 50/100",
                "status_before": "Current energy is 100/100",
            },
            {
                "action": "goto workshop",
                "cost": None,
                "inventory_after": None,
                "inventory_before": None,
                "reason": "Move to the workshop to craft wooden_boards.",
                "status_after": None,
                "status_before": None,
            },
            {
                "action": "craft wooden_board 3",
                "cost": "30 energy total (10 energy per item × 3)",
                "inventory_after": "Later inventory is {wood: 1, wooden_board: 3}",
                "inventory_before": "Current inventory is {wood: 10}",
                "reason": "Craft wooden_boards to prepare for book production.",
                "status_after": "Later energy is 20/100",
                "status_before": "Current energy is 50/100",
            },
            {
                "action": "goto home",
                "cost": None,
                "inventory_after": None,
                "inventory_before": None,
                "reason": "Go home to rest and recover energy.",
                "status_after": None,
                "status_before": None,
            },
            {
                "action": "sleep 8",
                "cost": "None",
                "inventory_after": None,
                "inventory_before": None,
                "reason": "The energy is too low, need to sleep to recover energy.",
                "status_after": "Later energy is 100/100",
                "status_before": "Current energy is 20/100",
            },
        ]
        return {"current_pointer": "Test_Put_False_Action_Info"}

    state = asyncio.run(utils.get_initial_state_from_db(432543, "websocket"))
    # pprint.pprint(state)
    logger.info(f"🚀 User {state['userid']} starting node engines")

    # pprint(state["public_data"]["market_data"])
    # print(state)
    # TEST REPLAN ROUTINES
    # asyncio.run(test_put_false_action_info(state))
    # logger.success(f"🌞 User {state['userid']} finished putting false action info")

    # asyncio.run(replan_meta_action_seq_new(state))
    # logger.success(
    #     f"🌞 User {state['userid']} finished replanning meta action sequence"
    # )

    # pprint.pprint(state["decision"]["meta_seq"])

    # pprint(state["decision"]["detailed_meta_seq"])

    # # TEST PLANNING ROUTINES
    asyncio.run(MainTest().test_plan(state))
