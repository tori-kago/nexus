from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
import redis
import json
import asyncio

app = FastAPI(title='Nexus Gateway')
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

@app.get('/')
def index():
    return {'status': 'Nexus Gateway is running'}

@app.post('/input')
async def receive_input(request: Request):
    data = await request.json()
    # 1. 發布到 Redis Pub/Sub
    r.publish('nexus.input', json.dumps(data))
    return {'status': 'published', 'channel': 'nexus.input'}

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    p = r.pubsub()
    p.subscribe('nexus.text')
    
    print('[*] WebSocket connected and subscribed to nexus.text')
    
    try:
        while True:
            # 檢查 Redis 訊息並推送到 WebSocket
            message = p.get_message(ignore_subscribe_messages=True)
            if message:
                await websocket.send_text(message['data'])
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f'[!] WebSocket error: {e}')
    finally:
        p.unsubscribe('nexus.text')
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
