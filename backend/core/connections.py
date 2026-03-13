import uuid
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: dict[uuid.UUID, WebSocket] = {}
        self._channels: dict[str, set[uuid.UUID]] = {}

    async def connect(self, agent_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        self._connections[agent_id] = websocket

    def disconnect(self, agent_id: uuid.UUID):
        self._connections.pop(agent_id, None)
        for channel_members in self._channels.values():
            channel_members.discard(agent_id)

    def subscribe(self, agent_id: uuid.UUID, channel: str):
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(agent_id)

    def unsubscribe(self, agent_id: uuid.UUID, channel: str):
        if channel in self._channels:
            self._channels[channel].discard(agent_id)

    async def send_to(self, agent_id: uuid.UUID, message: dict):
        ws = self._connections.get(agent_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(agent_id)

    async def broadcast(self, message: dict, exclude: uuid.UUID | None = None):
        disconnected = []
        for agent_id, ws in self._connections.items():
            if agent_id == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(agent_id)
        for agent_id in disconnected:
            self.disconnect(agent_id)

    async def broadcast_to_channel(self, channel: str, message: dict):
        members = self._channels.get(channel, set())
        disconnected = []
        for agent_id in members:
            ws = self._connections.get(agent_id)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(agent_id)
        for agent_id in disconnected:
            self.disconnect(agent_id)

    @property
    def active_count(self) -> int:
        return len(self._connections)

    @property
    def active_agents(self) -> list[uuid.UUID]:
        return list(self._connections.keys())
