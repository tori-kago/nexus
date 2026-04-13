import redis
import json
import time

def run_echo_brain():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    p = r.pubsub()
    p.subscribe('nexus.input')
    
    print('--- Echo Brain Started ---')
    for message in p.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            user_msg = data.get('message', '')
            
            # 模擬思考延遲
            time.sleep(0.5)
            
            # 發布回覆到 nexus.text
            response = {'response': f'Echo: {user_msg}'}
            r.publish('nexus.text', json.dumps(response))
            print(f'[Brain] Echoed: {user_msg}')

if __name__ == '__main__':
    run_echo_brain()
