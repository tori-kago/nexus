from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
import redis
import json
import asyncio
from uuid import uuid4
from src.shared.bus import MessageBus, CHANNELS
from src.shared.schemas import NexusEnvelope, MessageType

app = FastAPI(title='Nexus Gateway')
bus = MessageBus()

@app.get('/')
def index():
    return {'status': 'Nexus Gateway is running'}

@app.post('/input')
async def receive_input(request: Request):
    data = await request.json()
    trace_id = str(uuid4())
    
    # 封裝為符合 Protocol 的 Envelope
    envelope = NexusEnvelope(
        source="gateway:api",
        type=MessageType.INPUT,
        trace_id=trace_id,
        session_id=data.get("session_id"),  # 傳遞 session_id
        payload={
            "content": data.get("content", ""),
            "platform": data.get("platform", "web"),
            "raw_data": data
        }
    )
    
    # 透過 Bus 發布
    bus.publish_envelope(envelope)
    
    return {
        'status': 'published', 
        'trace_id': trace_id,
        'channel': CHANNELS['INPUT']
    }

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    p = bus.r.pubsub()
    p.subscribe(CHANNELS['TEXT'])
    
    print(f'[*] WebSocket connected and subscribed to {CHANNELS["TEXT"]}')
    
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
        p.unsubscribe(CHANNELS['TEXT'])
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
