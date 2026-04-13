import asyncio
import websockets
import json

async def listen():
    url = 'ws://localhost:8000/ws'
    print(f'[*] Connecting to {url}...')
    async with websockets.connect(url) as websocket:
        print('[+] Connected! Waiting for messages from Nexus...')
        while True:
            message = await websocket.recv()
            print(f'[Received from Nexus]: {message}')

if __name__ == '__main__':
    try:
        asyncio.run(listen())
    except KeyboardInterrupt:
        print('Stopped.')
