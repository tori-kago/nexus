import redis
import json
import asyncio
import re
from src.brain.logic import BrainEngine
from src.shared.bus import MessageBus, CHANNELS
from src.shared.schemas import NexusEnvelope, MessageType
from pydantic import ValidationError

async def handle_envelope(envelope: NexusEnvelope, engine: BrainEngine, bus: MessageBus):
    trace_id = envelope.trace_id
    session_id = envelope.session_id or "default_session"
    
    if envelope.type == MessageType.INPUT:
        user_text = envelope.payload.get('content', '')
        print(f'[Brain] 📥 [INPUT] Trace: {trace_id} | Input: {user_text[:30]}...')
        
        # 執行推理循環
        response_text = await engine.run(trace_id, session_id, user_text)
        
        # 解析情緒與清理內容
        emotion = "focused"
        emotion_match = re.search(r"\[EMOTION: (.*?)\]", response_text)
        if emotion_match:
            emotion = emotion_match.group(1).lower().strip()
        
        clean_content = re.sub(r"\[EMOTION: .*?\]", "", response_text).strip()
        
        # 發送最終回覆
        output_envelope = NexusEnvelope(
            source="brain:worker",
            type=MessageType.TEXT,
            trace_id=trace_id,
            session_id=session_id,
            payload={
                "content": clean_content,
                "emotion": emotion
            }
        )
        bus.publish_envelope(output_envelope)
        print(f'[Brain] ✅ [REPLY] Trace: {trace_id}')

    elif envelope.type == MessageType.HEARTBEAT:
        print(f'[Brain] 💓 [HEARTBEAT] Trace: {trace_id}. Triggering proactive reflection...')
        # 心跳觸發的被動行為：讓引擎進行一次「自我反思」
        response_text = await engine.run(trace_id, session_id, "", is_proactive=True)
        
        if response_text and response_text != "__IGNORE__":
            # 解析情緒與清理內容
            emotion = "curious"
            emotion_match = re.search(r"\[EMOTION: (.*?)\]", response_text)
            if emotion_match:
                emotion = emotion_match.group(1).lower().strip()
            
            clean_content = re.sub(r"\[EMOTION: .*?\]", "", response_text).strip()
            
            output_envelope = NexusEnvelope(
                source="brain:proactive",
                type=MessageType.TEXT,
                trace_id=trace_id,
                session_id=session_id,
                payload={
                    "content": clean_content,
                    "emotion": emotion,
                    "is_proactive": True
                }
            )
            bus.publish_envelope(output_envelope)
            print(f'[Brain] 📢 Proactive engagement sent: {clean_content[:30]}...')
        else:
            print(f'[Brain] 😴 Proactive check completed: No action needed.')

async def run_brain_worker():
    bus = MessageBus()
    p = bus.r.pubsub()
    p.subscribe(CHANNELS['INPUT'], CHANNELS['HEARTBEAT'])
    
    engine = BrainEngine()
    
    print('--- Nexus Autonomous Brain Worker (v2.0) Started ---')
    print(f'[*] Subscribed to {CHANNELS["INPUT"]} and {CHANNELS["HEARTBEAT"]}')
    
    while True:
        try:
            message = p.get_message(ignore_subscribe_messages=True)
            if message:
                raw_data = message['data']
                try:
                    if hasattr(NexusEnvelope, "model_validate_json"):
                        envelope = NexusEnvelope.model_validate_json(raw_data)
                    else:
                        envelope = NexusEnvelope.parse_raw(raw_data)
                    
                    # 異步處理，不阻塞監聽循環
                    asyncio.create_task(handle_envelope(envelope, engine, bus))
                    
                except ValidationError as ve:
                    print(f'[Brain JSON Error] Invalid Envelope format: {ve}')
                except Exception as e:
                    print(f'[Brain Processing Error] {e}')
        except Exception as bus_err:
            print(f'[Bus Error] {bus_err}')
        
        await asyncio.sleep(0.05)

if __name__ == '__main__':
    asyncio.run(run_brain_worker())
