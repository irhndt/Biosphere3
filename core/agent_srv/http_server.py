from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import Request
from core.agent_srv.node_engines import *
import core.agent_srv.utils as utils
import asyncio
from loguru import logger

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/")
async def root():
    return {"message": "Welcome to the API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/plan")
async def plan(request: Request):
    data = await request.json()
    state = await utils.get_initial_state_from_db(data["userid"], "http")
    # pprint.pprint(state)
    logger.info(f"🚀 User {state['userid']} starting node engines")

    await generate_daily_objective(state)
    logger.success(f"🌞 User {state['userid']} finished daily objective")
    await generate_crafting_and_trading_sequence(state)
    logger.success(f"🌞 User {state['userid']} finished crafting and trading")

    return {"plan": state["decision"]["expanded_meta_seq"]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
