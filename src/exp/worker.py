import redis
import json
import asyncio
from datetime import datetime
from uuid import uuid4
from src.exp.logic import ExpressionEngine
from src.shared.schemas import NexusEnvelope, MessageType, CommandPayload

async def run_exp_worker():
    # 1. 初始化 Redis 連線
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    p = r.pubsub()
    p.subscribe('nexus.text')
    
    # 2. 初始化表達邏輯
    engine = ExpressionEngine()
    
    print('--- Expression Engine (NUP v1.0) Started ---')
    
    # 3. 監聽回覆並提取表現指令
    while True:
        message = p.get_message(ignore_subscribe_messages=True)
        if message:
            try:
                # 解析傳入的 NexusEnvelope
                envelope_data = json.loads(message['data'])
                trace_id = envelope_data.get('trace_id')
                session_id = envelope_data.get('session_id')
                payload = envelope_data.get('payload', {})
                text_content = payload.get('content', '')
                emotion = payload.get('emotion', '')
                
                # 1. 處理文字中的表情與指令
                commands = engine.process(text_content)
                
                # 2. 🆕 如果 payload 有 emotion，也將其加入指令流
                if emotion and emotion != "focused": # focused 是預設，可以選擇性忽略或轉化
                    commands.append({"type": "expression", "value": emotion})
                
                for cmd in commands:
                    # 封裝為 NUP Command 封包
                    command_envelope = NexusEnvelope(
                        source="expression_engine",
                        type=MessageType.COMMAND,
                        trace_id=trace_id,
                        session_id=session_id,
                        payload={
                            "action": "play_animation" if cmd['type'] == 'expression' else cmd['type'],
                            "params": {"value": cmd['value']}
                        }
                    )
                    
                    # 將指令發布到 nexus.command 頻道
                    r.publish('nexus.command', command_envelope.json())
                    print(f'[Exp] Sent COMMAND for Trace: {trace_id[:8]} -> {cmd["value"]}')
                    
            except Exception as e:
                print(f'[Exp Error] {e}')
        
        await asyncio.sleep(0.1)

if __name__ == '__main__':
    asyncio.run(run_exp_worker())
