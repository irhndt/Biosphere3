import asyncio
import websockets
import json

characterId = 448450
characterId2 = 240929

requests = {
    "heartbeat": {
        "characterId": characterId,
        "messageCode": 0,
        "messageName": "heartbeat",
        "data": {"msg": "this is a message to keep connection alive"},
    },
    "connectionInit": {
        "characterId": characterId,
        "messageCode": 1,
        "messageName": "connectionInit",
        "data": {"msg": "client request character init"},
    },
    "eventInfo": {
        "characterId": characterId,
        "messageCode": 2,
        "messageName": "eventInfo",
        "data": {"msg": "event string", "gameTime": "time"},
    },
    "actionResult": {
        "characterId": characterId,
        "messageCode": 3,
        "messageName": "actionresult",
        "data": {
            "actionName": "name",
            "actionCode": "code",
            "result": "result",
            "gameTime": "time",
            "msg": "msg",
        },
    },
    "gameTime": {
        "characterId": characterId,
        "messageCode": 5,
        "messageName": "gameTime",
        "data": {"msg": "event string", "gameTime": "time"},
    },
    "conversation": {
        "characterId": characterId,
        "messageCode": 100,
        "messageName": "to_agent",
        "data": {
            "from_id": characterId,
            "to_id": characterId2,
            "latest_message": {
                "playerName": "message_info",
            },
            "Finish": [False, False],
        },
    },
}


async def send_request(websocket, request):
    message = json.dumps(request)
    await websocket.send(message)
    if request["messageName"] != "heartbeat":
        print(f"Sent: {message}")


async def receive_response(websocket):
    while True:
        response = await websocket.recv()
        message = json.loads(response)
        if message["messageName"] != "heartbeat":
            print(f"Received: {message}")


async def send_heartbeat(websocket):
    while True:
        await send_request(websocket, requests["heartbeat"])
        await asyncio.sleep(30)


async def send_game_time(websocket):
    while True:
        await send_request(websocket, requests["gameTime"])
        await asyncio.sleep(300)


async def send_event_info(websocket):
    while True:
        await asyncio.sleep(300)
        requests["eventInfo"]["data"]["msg"] = "ActionList Empty"
        await send_request(websocket, requests["eventInfo"])


async def main():
    uri = "ws://localhost:6789"
    async with websockets.connect(uri) as websocket:
        await send_request(websocket, requests["connectionInit"])

        receive_task = asyncio.create_task(receive_response(websocket))

        heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
        game_time_task = asyncio.create_task(send_game_time(websocket))
        event_info_task = asyncio.create_task(send_event_info(websocket))

        await asyncio.gather(
            receive_task, heartbeat_task, game_time_task, event_info_task
        )


if __name__ == "__main__":
    asyncio.run(main())
