import redis
import json
import asyncio
from langchain_core.messages import HumanMessage
from src.brain.logic import create_brain_graph

async def run_brain_worker():
    # 1. 初始化 Redis 連線
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    p = r.pubsub()
    p.subscribe('nexus.input')
    
    # 2. 初始化 LangGraph 邏輯
    graph = create_brain_graph()
    
    print('--- LangGraph Brain Worker (via Gemini CLI) Started ---')
    
    # 3. 異步監聽訊息並處理
    while True:
        # 這裡使用異步方式檢查 Redis
        message = p.get_message(ignore_subscribe_messages=True)
        if message:
            try:
                # 解析輸入資料
                input_data = json.loads(message['data'])
                user_text = input_data.get('message', '')
                
                # 調用 LangGraph 大腦思考
                # 這裡使用 invoke 並傳入初始狀態
                # 因為是 Demo，這裡還沒加入真正的對話持久化 (如 SQLite Checkpointer)
                result = graph.invoke({"messages": [HumanMessage(content=user_text)]})
                
                # 獲取模型最後的回覆
                last_message = result['messages'][-1]
                response_text = last_message.content
                
                # 將回覆推送到 Redis
                response_payload = {"response": response_text}
                r.publish('nexus.text', json.dumps(response_payload))
                print(f'[Brain] Replied: {response_text[:50]}...')
            except Exception as e:
                print(f'[Brain Error] {e}')
        
        await asyncio.sleep(0.1) # 避免 CPU 消耗過高

if __name__ == '__main__':
    asyncio.run(run_brain_worker())
