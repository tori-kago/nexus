import json
import time
import uuid
import redis
from src.shared.bus import CHANNELS
from src.shared.schemas import NexusEnvelope, MessageType

def test_reasoning_loop():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # 1. 訂閱 TEXT 與 THOUGHT 頻道以觀察輸出
    p = r.pubsub()
    p.subscribe(CHANNELS['TEXT'], CHANNELS['THOUGHT'])
    
    trace_id = f"test-{uuid.uuid4()}"
    
    # 2. 發送一個需要多步思考的請求
    input_envelope = NexusEnvelope(
        source="test_client",
        type=MessageType.INPUT,
        trace_id=trace_id,
        payload={
            "content": "我最近很累，而且我決定明天要去爬山，請幫我記住這件事並給我一點鼓勵 (´Д` )"
        }
    )
    
    print(f"[*] Sending test input... Trace: {trace_id}")
    r.publish(CHANNELS['INPUT'], input_envelope.json())
    
    # 3. 監聽回饋
    print("[*] Waiting for thoughts and final reply...")
    start_time = time.time()
    while time.time() - start_time < 30: # 等待 30 秒
        message = p.get_message(ignore_subscribe_messages=True)
        if message:
            data = json.loads(message['data'])
            m_type = data.get('type')
            payload = data.get('payload', {})
            
            if m_type == 'thought':
                state = payload.get('state')
                reasoning = payload.get('reasoning')
                print(f"  [Thought] {state}: {reasoning}")
            elif m_type == 'text':
                content = payload.get('content')
                emotion = payload.get('emotion')
                print(f"\n[Nexus Final Reply] ({emotion})")
                print(f"Content: {content}")
                return
        time.sleep(0.1)
    
    print("[!] Test timed out.")

if __name__ == "__main__":
    test_reasoning_loop()
