import redis
import json
import asyncio
from typing import Callable, Any

class MessageBus:
    def __init__(self, host='localhost', port=6379, db=0):
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.pubsub = self.r.pubsub()

    def publish(self, channel: str, message: dict):
        """將 JSON 訊息發布到指定頻道"""
        self.r.publish(channel, json.dumps(message))

    async def listen(self, channel: str, handler: Callable):
        """訂閱並監聽頻道"""
        p = self.r.pubsub()
        p.subscribe(channel)
        print(f'[*] Listening on channel: {channel}')
        for message in p.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    await handler(data)
                except Exception as e:
                    print(f'[!] Error: {e}')

CHANNELS = {
    'INPUT': 'nexus.input',
    'THOUGHT': 'nexus.thought',
    'TEXT': 'nexus.text',
    'COMMAND': 'nexus.command'
}
