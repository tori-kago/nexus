import redis
import json
import time
import uuid
import requests
from src.shared.schemas import NexusEnvelope

def test_protocol_flow():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    p = r.pubsub()
    
    # 訂閱所有相關頻道
    channels = ['nexus.input', 'nexus.thought', 'nexus.text']
    p.subscribe(*channels)
    
    print("[Test] Subscribed to channels. Sending input to Gateway...")
    
    # 模擬 Gateway 請求 (或者直接發布到 Bus)
    # 這裡假設 Gateway 正在運行在 localhost:8000
    try:
        response = requests.post("http://localhost:8000/input", json={"content": "你好，請自我介紹並測試反思機制 [REFLECT:USER] 喜歡測試。"})
        trace_id = response.json().get("trace_id")
        print(f"[Test] Gateway accepted request. Trace ID: {trace_id}")
    except Exception as e:
        print(f"[Test] Gateway not reachable, fallback to direct Bus publish. Error: {e}")
        trace_id = str(uuid.uuid4())
        r.publish('nexus.input', json.dumps({
            "id": str(uuid.uuid4()),
            "timestamp": "now",
            "source": "test:manual",
            "type": "input",
            "trace_id": trace_id,
            "payload": {"content": "你好，請自我介紹 [REFLECT:USER] 喜歡測試。", "platform": "test"}
        }))

    # 觀察訊息流
    start_time = time.time()
    received_count = 0
    while time.time() - start_time < 15: # 最多等 15 秒
        msg = p.get_message(ignore_subscribe_messages=True)
        if msg:
            data = json.loads(msg['data'])
            msg_type = data.get('type')
            msg_trace = data.get('trace_id')
            
            if msg_trace == trace_id:
                print(f"\n[RECEIVED ON {msg['channel']}]")
                print(f"Type: {msg_type}")
                print(f"Payload: {data.get('payload')}")
                received_count += 1
                
                if msg_type == 'text':
                    print("\n[Test] Final response received. Test Success!")
                    break
        time.sleep(0.1)

    if received_count < 2:
        print("\n[Test] Failed: Did not receive enough protocol steps (Thinking/Text).")

if __name__ == "__main__":
    test_protocol_flow()
