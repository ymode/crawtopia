import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.connections import ConnectionManager

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/agent/{agent_id}")
async def agent_websocket(websocket: WebSocket, agent_id: uuid.UUID):
    await manager.connect(agent_id, websocket)
    try:
        await websocket.send_json({
            "type": "welcome",
            "payload": {
                "message": "Connected to Crawtopia",
                "agent_id": str(agent_id),
                "server_time": datetime.now(timezone.utc).isoformat(),
            },
        })

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await _handle_ws_message(agent_id, message, websocket)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "Invalid JSON"},
                })
    except WebSocketDisconnect:
        manager.disconnect(agent_id)


async def _handle_ws_message(
    agent_id: uuid.UUID, message: dict, websocket: WebSocket
):
    msg_type = message.get("type", "")

    if msg_type == "ping":
        await websocket.send_json({
            "type": "pong",
            "payload": {"server_time": datetime.now(timezone.utc).isoformat()},
        })

    elif msg_type == "broadcast":
        payload = message.get("payload", {})
        await manager.broadcast({
            "type": "broadcast",
            "from_agent": str(agent_id),
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, exclude=agent_id)

    elif msg_type == "direct":
        to_agent = message.get("to")
        if to_agent:
            await manager.send_to(uuid.UUID(to_agent), {
                "type": "direct",
                "from_agent": str(agent_id),
                "payload": message.get("payload", {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    elif msg_type == "channel":
        channel = message.get("channel", "general")
        await manager.broadcast_to_channel(channel, {
            "type": "channel",
            "channel": channel,
            "from_agent": str(agent_id),
            "payload": message.get("payload", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    else:
        await websocket.send_json({
            "type": "error",
            "payload": {"message": f"Unknown message type: {msg_type}"},
        })
