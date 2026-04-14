import redis
import json
import asyncio
from src.exp.logic import ExpressionEngine

async def run_exp_worker():
    # 1. 初始化 Redis 連線
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    p = r.pubsub()
    p.subscribe('nexus.text')
    
    # 2. 初始化表達邏輯
    engine = ExpressionEngine()
    
    print('--- Expression Engine Worker Started ---')
    
    # 3. 監聽回覆並提取表現指令
    while True:
        message = p.get_message(ignore_subscribe_messages=True)
        if message:
            try:
                data = json.loads(message['data'])
                text = data.get('response', '')
                
                # 處理表情與指令
                commands = engine.process(text)
                
                for cmd in commands:
                    # 將指令發布到 nexus.command 頻道
                    r.publish('nexus.command', json.dumps(cmd))
                    print(f'[Exp] Published Command: {cmd}')
            except Exception as e:
                print(f'[Exp Error] {e}')
        
        await asyncio.sleep(0.1)

if __name__ == '__main__':
    asyncio.run(run_exp_worker())
