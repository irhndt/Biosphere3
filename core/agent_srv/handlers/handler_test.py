from core.agent_srv.node_model import RunningState
from core.agents.graph_instance import LangGraphInstance
from core.agent_srv.handlers import *
from loguru import logger


class MainTest:
    def __init__(self):
        self.planner = PlanningHandler()
        self.career_cv = CareerCVHandler()
        self.accommodation = AccommodationHandler()
        self.reflection = ReflectionHandler()
        self.instance = LangGraphInstance(755928)
        self.instance.state = asyncio.run(
            utils.get_initial_state_from_db(755928, "websocket")
        )
        self.state = self.instance.state

    async def test_plan(self):
        await self.planner.generate_daily_objective(self.state)
        await self.planner.generate_crafting_and_trading_sequence(self.state)

    async def test_replan(self):
        false_action_info = {
            "actionName": "goto forest",
            "msg": "No location named 'forest'.",
        }
        self.state["false_action_queue"].put_nowait(false_action_info)
        self.state["decision"]["detailed_meta_seq"] = [
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
        await self.planner.generate_daily_objective(self.state)
        await self.planner.replan_meta_action(self.state)

    async def test_cv(self):
        msg = {
            "characterId": 755928,
            "messageCode": 9,
            "messageName": "new_day",
            "data": {
                "health": 100,
                "studyXp": 10,
                "education": "None",
                "week": 1,
                "date": 1,
                "msg": "this is a message to sync new day",
            },
        }

        await self.career_cv.generate_cv(self.instance, msg)

    async def test_accommodation(self):
        await self.accommodation.generate_accommodation_decision(self.state)

    async def test_reflection(self):
        await self.reflection.generate_reflection(self.state)


if __name__ == "__main__":
    import asyncio
    import core.agent_srv.utils as utils

    # state = asyncio.run(utils.get_initial_state_from_db(755928, "websocket"))
    # # pprint.pprint(state)
    # logger.info(f"🚀 User {state['userid']} starting node engines")

    # pprint(state["public_data"]["market_data"])
    # print(state)
    mainTest = MainTest()
    # TEST REPLAN ROUTINES
    # asyncio.run(mainTest.test_replan(state))

    # # TEST PLANNING ROUTINES
    # asyncio.run(mainTest.test_plan())

    ## TEST CV ROUTINES
    asyncio.run(mainTest.test_cv())

    ## TEST ACCOMMODATION ROUTINES
    # asyncio.run(mainTest.test_accommodation())
