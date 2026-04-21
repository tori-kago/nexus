import asyncio
import websockets
import json

async def test_nexus_ws():
    url = 'ws://localhost:8000/ws'
    print(f'[*] Connecting to {url}...')
    try:
        async with websockets.connect(url) as websocket:
            print('[+] Connected!')
            
            # 發送一條測試訊息
            test_msg = {"content": "你好，記得我是誰嗎？"}
            print(f'[Sending]: {test_msg}')
            await websocket.send(json.dumps(test_msg))
            
            # 持續接收回覆直到最終回覆
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("type") == "thought":
                    print(f'  [Thinking] {data.get("state")}: {data.get("content")[:50]}...')
                elif data.get("type") == "text":
                    print(f'[Final Reply]: {data.get("content")}')
                    break
                    
    except Exception as e:
        print(f'[Error]: {e}')

if __name__ == '__main__':
    asyncio.run(test_nexus_ws())
