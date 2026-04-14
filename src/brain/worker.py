import redis
import json
import asyncio
from langchain_core.messages import HumanMessage
from src.brain.logic import create_brain_graph
from src.shared.bus import MessageBus, CHANNELS
from src.shared.schemas import NexusEnvelope, MessageType
from pydantic import ValidationError

async def run_brain_worker():
    # 1. 初始化 Bus
    bus = MessageBus()
    p = bus.r.pubsub()
    p.subscribe(CHANNELS['INPUT'])
    
    # 2. 初始化 LangGraph 邏輯
    graph = create_brain_graph()
    
    print('--- LangGraph Brain Worker (NUP v1.0) Started ---')
    print(f'[*] Subscribed to {CHANNELS["INPUT"]}')
    
    # 3. 異步監聽訊息並處理
    while True:
        try:
            # 使用非阻塞方式獲取訊息
            message = p.get_message(ignore_subscribe_messages=True)
            if message:
                raw_data = message['data']
                try:
                    # 相容 Pydantic v1/v2 的解析方式
                    if hasattr(NexusEnvelope, "model_validate_json"):
                        input_envelope = NexusEnvelope.model_validate_json(raw_data)
                    else:
                        input_envelope = NexusEnvelope.parse_raw(raw_data)
                        
                    trace_id = input_envelope.trace_id
                    user_text = input_envelope.payload.get('content', '')
                    
                    print(f'[Brain] 📥 Received Trace: {trace_id} | Input: {user_text[:30]}...')
                    
                    # 調用 LangGraph 大腦思考
                    initial_state = {
                        "messages": [HumanMessage(content=user_text)],
                        "trace_id": trace_id
                    }
                    
                    # 使用 to_thread 避免阻塞事件循環 (graph.invoke 通常是同步的)
                    result = await asyncio.to_thread(graph.invoke, initial_state)
                    
                    # 獲取模型最後的回覆
                    last_message = result['messages'][-1]
                    response_text = last_message.content
                    
                    # 將回覆封裝為 Envelope 並發布
                    output_envelope = NexusEnvelope(
                        source="brain:worker",
                        type=MessageType.TEXT,
                        trace_id=trace_id,
                        payload={
                            "content": response_text,
                            "emotion": "focused"
                        }
                    )
                    bus.publish_envelope(output_envelope)
                    print(f'[Brain] ✅ Success Trace: {trace_id}')
                    
                except ValidationError as ve:
                    print(f'[Brain JSON Error] Invalid Envelope format: {ve}')
                except Exception as e:
                    print(f'[Brain Processing Error] {e}')
                    # 嘗試發送錯誤訊號至 Thought 頻道
                    try:
                        temp_data = json.loads(raw_data)
                        temp_trace = temp_data.get('trace_id', 'unknown')
                        bus.publish_envelope(NexusEnvelope(
                            source="brain:worker",
                            type=MessageType.THOUGHT,
                            trace_id=temp_trace,
                            payload={"state": "error", "reasoning": str(e)}
                        ))
                    except: pass
        except Exception as bus_err:
            print(f'[Bus Error] {bus_err}')
        
        await asyncio.sleep(0.05)

if __name__ == '__main__':
    asyncio.run(run_brain_worker())
