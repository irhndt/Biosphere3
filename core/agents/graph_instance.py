import sys
import traceback

sys.path.append(".")

import asyncio
import json
import time
from pprint import pprint
from loguru import logger
import websockets
from langgraph.graph import StateGraph
from core.agent_srv.node_engines import *
from core.agent_srv.node_model import RunningState
from core.agent_srv.utils import (
    get_initial_state_from_db,
    save_decision_to_db,
    save_action_to_db,
    update_state_daily,
    clear_decision,
)
from core.agent_srv.handlers import *


class LangGraphInstance:
    """
    Initializes the state, sets up asynchronous tasks for message processing, event scheduling, and runs the workflow graph.
    """

    def __init__(self, user_id, websocket=None):
        self.user_id = user_id
        self.websocket = websocket
        self.signal = None
        self.state = {}
        self.message_log = []

        self.websocket_lock = None
        self.graph = None
        self.graph_config = {"recursion_limit": 1e10}
        self.logger = logger.bind(agent_instance=True)

        # Asynchronous tasks
        self.msg_processor_task = None
        self.event_scheduler_task = None
        self.task = None
        self.routine_tasks = None

        # Handlers setup
        self.planner = PlanningHandler()
        self.career_cv = CareerCVHandler()
        self.accommodation = AccommodationHandler()
        self.reflection = ReflectionHandler()

    @classmethod
    async def create(cls, user_id, websocket=None):
        self = cls(user_id, websocket)
        initial_state = await get_initial_state_from_db(user_id, websocket)
        self.state = initial_state

        self.state["instance"] = self
        self.websocket_lock = asyncio.Lock()
        self.graph = self._get_workflow()
        self.graph_config = {"recursion_limit": 1e10}
        self.start_time = time.time()

        self.msg_processor_task = asyncio.create_task(self.msg_processor())
        # self.event_scheduler_task = asyncio.create_task(self.event_scheduler())
        self.schedule_event("PLAN")
        self.logger.info(f"User {self.user_id} workflow initialized")
        self.task = asyncio.create_task(self.a_run())

        return self

    async def msg_processor(self):
        """
        Continuously processes incoming messages from the message queue.
        """
        while True:
            try:
                msg = await self.state["message_queue"].get()
                message_name = msg.get("messageName")
                message_code = msg.get("messageCode")
                message_data = msg.get("data")
                if message_code >= 100:  # Ignore Conversation Messages
                    pass
                elif message_name == "actionresult":
                    self.logger.info(
                        f"🏃 User {self.user_id}: Received action result: {msg['data']}"
                    )
                    self.state["decision"]["action_result"].append(message_data["msg"])
                    if message_data.get("actionName").startswith("goto"):
                        save_action_to_db(self.user_id, message_data)
                    # If the action result is False, put REPLAN into event_queue
                    self.state["decision"]["expanded_meta_seq"].popleft()
                    if msg["data"]["result"] is False:
                        try:
                            self.logger.info(
                                f"❌ User {self.user_id}: Put REPLAN into event_queue"
                            )
                            self.state["false_action_queue"].put_nowait(msg["data"])
                            self.schedule_event("REPLAN")
                        except Exception as e:
                            self.logger.error(
                                f"User {self.user_id}: Error putting REPLAN into event_queue: {e}"
                            )
                    else:
                        self.logger.info(
                            f"User {self.user_id} current meta action list: {list(self.state['decision']['expanded_meta_seq'])}"
                        )
                elif message_name == "onestep":
                    self.schedule_event("PLAN")
                elif message_name == "check":
                    pprint(self.state["decision"]["action_result"])
                elif message_name == "queue_visualizer":
                    pprint(self.state["event_queue"])
                elif (
                    message_name == "eventInfo"
                    and message_data
                    and message_data.get("msg") == "ActionList Empty"
                ):
                    logger.info(
                        f"User {self.state['userid']} received ActionList Empty!"
                    )
                    self.schedule_event("PLAN")
                elif (
                    message_name == "accommodation_event"
                    and message_data
                    and message_data.get("msg") == "House rent will expire tomorrow"
                ):
                    self.schedule_event("ACCOMMODATION_EVENT")
                elif message_name == "new_day":
                    update_state_daily(
                        self.state,
                        message_data.get("day", self.state["meta"]["day"] + 1),
                    )
                    self.schedule_event("CHARACTER_ARC")
                    self.schedule_event("DAILY_REFLECTION")
                    # await self.career_cv.generate_cv(self.state["instance"], msg)
                    await asyncio.sleep(60)
                    clear_decision(self.state)
                elif message_name == "cv_submission":
                    await self.career_cv.generate_cv(self.state["instance"], msg)
                else:
                    self.logger.error(
                        f"User {self.user_id}: Unknown message: {message_name}"
                    )
            except Exception as e:
                self.logger.error(f"User {self.user_id}: Error in msg_processor: {e}")
                self.logger.error(traceback.format_exc())
                raise e

    async def event_scheduler(self):
        try:
            plan_task = asyncio.create_task(self.run_event("PLAN", 300))
            reflection_task = asyncio.create_task(
                self.run_event("DAILY_REFLECTION", 600)
            )
            character_arc_task = asyncio.create_task(
                self.run_event("CHARACTER_ARC", 900)
            )
            self.routine_tasks = [plan_task, reflection_task, character_arc_task]
            await asyncio.gather(*self.routine_tasks)
        except Exception as e:
            self.logger.error(f"User {self.user_id}: Error in event_scheduler: {e}")

    def schedule_event(self, event):
        self.state["event_queue"].put_nowait(event)
        self.logger.info(f"🚦 User {self.user_id}: Scheduled event: {event}")

    async def event_router(self, state: RunningState):
        while True:
            event = await state["event_queue"].get()
            self.logger.info(f"🚦 User {self.user_id}: Event: {event}")

            if event == "PLAN":
                return "Objectives_planner"
            elif event == "CHARACTER_ARC":
                return "Character_Arc"
            elif event == "REPLAN":
                return "Replan_Action"
            elif event == "DAILY_REFLECTION":
                return "Daily_Reflection"
            elif event == "ACCOMMODATION_EVENT":
                return "Accommodation_Decision"
            else:
                self.logger.error(f"User {self.user_id}: Unknown event: {event}")

    async def run_event(self, event_name, interval):
        try:
            while True:
                await asyncio.sleep(interval)

                if self.signal == "TERMINATE":
                    self.logger.error(
                        f"⛔ User {self.user_id}'s Task run_event terminated due to termination signal."
                    )
                    break
                if event_name not in list(self.state["event_queue"]._queue):
                    self.schedule_event(event_name)
        except Exception as e:
            self.logger.error(f"User {self.user_id}: Error in run_event: {e}")
            raise e

    def _get_workflow(self):
        workflow = StateGraph(RunningState)
        workflow.add_node("Sensing_Route", sensing_environment)
        workflow.add_node("Objectives_planner", self.planner.generate_daily_objective)
        workflow.add_node(
            "meta_action_sequence", self.planner.generate_crafting_and_trading_sequence
        )
        workflow.add_node("Character_Arc", self.reflection.generate_arc)
        workflow.add_node("Daily_Reflection", self.reflection.generate_reflection)
        workflow.add_node("Replan_Action", self.planner.replan_meta_action)
        workflow.add_node(
            "Accommodation_Decision", self.accommodation.generate_accommodation_decision
        )

        workflow.set_entry_point("Sensing_Route")

        workflow.add_conditional_edges("Sensing_Route", self.event_router)
        workflow.add_edge("Objectives_planner", "meta_action_sequence")
        workflow.add_edge("Replan_Action", "Sensing_Route")
        workflow.add_edge("meta_action_sequence", "Sensing_Route")
        workflow.add_edge("Character_Arc", "Sensing_Route")
        workflow.add_edge("Daily_Reflection", "Sensing_Route")
        workflow.add_edge("Accommodation_Decision", "Sensing_Route")

        return workflow.compile()

    async def a_run(self):
        try:
            await self.graph.ainvoke(self.state, config=self.graph_config)
        except Exception as e:
            self.signal = "TERMINATE"

            self.logger.error(f"User {self.user_id} Error in workflow: {e}")
            self.logger.error(traceback.format_exc())
            self.logger.error("⛔ Task a_run terminated due to termination signal.")
            self.task.cancel()
            # self.routine_tasks.cancel()

    async def send_message(self, message):
        async with self.websocket_lock:
            if self.websocket is None or self.websocket.closed:
                self.logger.error(
                    f"⛔ User {self.user_id}: WebSocket is not connected."
                )
                self.signal = "TERMINATE"
                return
            try:
                await self.websocket.send(json.dumps(message))
                self.logger.info(f"📤 User {self.user_id}: Sent message: {message}")
            except websockets.ConnectionClosed:
                self.logger.warning(
                    f"User {self.user_id}: WebSocket connection closed during send."
                )
                self.signal = "TERMINATE"
            except Exception as e:
                self.logger.error(f"User {self.user_id}: Error sending message: {e}")

    def log_message(self, direction: str, message: dict):
        self.message_log.append(
            {
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "direction": direction,
                "message": message,
            }
        )
