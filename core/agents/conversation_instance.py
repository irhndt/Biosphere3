from core.conversation_srv.conversation_engines import *
import asyncio


class ConversationInstance:
    def __init__(self, user_id, websocket=None):
        self.user_id = user_id
        self.websocket = websocket
        self.plan_signal = False
        self.is_initial = True
        self.state = initialize_conversation_state(self.user_id, self.websocket)
        self.graph = start_conversation_workflow()
        self.graph_config = {"recursion_limit": 1000}
        self.msg_processor_task = None
        self.reply_message_task = None
        self.clear_readonly_task = None
        self.plan_start_task = None
        self.logger = logger.bind(conversation_instance=True)

    @classmethod
    async def create(cls, user_id, websocket=None):
        self = cls(user_id, websocket)
        
        # create tasks for conversation agent
        self.plan_start_task = asyncio.create_task(self.run_workflow())

        self.logger.info(f"User {self.user_id} conversation client initialized")
        return self

    # listener
    async def listener(self, data):
        if self.is_initial:
            self.plan_signal = True
            self.is_initial = False
        websocket = self.state["websocket"]

    # plan-and-start workflow
    async def run_workflow(self):
        while True:
            if self.plan_signal:
                try:
                    self.logger.info(
                        f"🏃 User {self.user_id}: Begin planning for today's conversations..."
                    )
                    await self.graph.ainvoke(self.state, config=self.graph_config)
                    self.plan_signal = False
                    day, hour, minute = calculate_game_time(real_time=datetime.now())
                    time_gap = ((24-hour)*60*60+(0-minute)*60)//7+(self.user_id//1000)
                    self.logger.info(
                        f"Next planning workflow will start in {time_gap} seconds."
                    )
                    await asyncio.sleep(time_gap)
                    self.logger.info(f"🏃 User {self.user_id}: LET'S HAVE A NEW PLAN!")
                    self.plan_signal = True
                except Exception as e:
                    self.logger.error(
                        f"User {self.user_id} Error in conversation planning and starting workflow: {e}"
                    )
                    time_gap = 300
                    self.logger.info(
                        f"Next planning workflow will start in {time_gap} seconds."
                    )
                    await asyncio.sleep(time_gap)
                    self.plan_signal = True
            else:
                await asyncio.sleep(10)

