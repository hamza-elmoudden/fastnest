from fastnest.core.websocket import (
    WebSocketGateway, SubscribeMessage, OnConnect, OnDisconnect, WebSocketClient,
)


@WebSocketGateway("/ws/${name}")
class ${ClassName}Gateway:
    @OnConnect()
    async def on_connect(self, client: WebSocketClient):
        # TODO: handle new connection
        await client.send({"event": "connected", "id": client.id})

    @OnDisconnect()
    async def on_disconnect(self, client: WebSocketClient):
        # TODO: handle disconnection
        pass

    @SubscribeMessage("message")
    async def handle_message(self, data, client: WebSocketClient):
        # TODO: handle incoming message
        await client.send({"event": "echo", "data": data})
