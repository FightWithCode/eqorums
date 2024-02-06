from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json
import requests

from asgiref.sync import sync_to_async


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        print("chat websocket connected")
        await self.accept()
        self.kwargs = self.scope["url_route"]["kwargs"]
        await self.channel_layer.group_add(self.kwargs.get('grp_name'), self.channel_name)

    async def chat_message(self, event):
        print(event)
        await self.send_json(event['msg'])

    async def receive(self, text_data=None, bytes_data=None):
        print("receive...", text_data)
        await self.channel_layer.group_send(self.kwargs.get('grp_name'), {'type': 'chat.message', 'msg': json.loads(text_data)})
        await self.channel_layer.group_send(json.loads(text_data).get("url", "f"), {'type': 'chat.message', 'msg': json.loads(text_data)})

    async def disconnect(self, close_code):
        print("Webbsocket disconnect...")
        await self.channel_layer.group_discard(self.kwargs.get('grp_name'), self.channel_name)
