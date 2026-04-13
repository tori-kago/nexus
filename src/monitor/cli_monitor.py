import redis
import json
import sys
from datetime import datetime

def run_monitor():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    p = r.pubsub()
    # 訂閱所有 nexus 開頭的頻道
    p.psubscribe('nexus.*')
    
    print('--- Nexus CLI Monitor Started ---')
    print('Listening on all nexus.* channels...')
    
    try:
        for message in p.listen():
            if message['type'] == 'pmessage':
                channel = message['channel']
                data = message['data']
                time_str = datetime.now().strftime('%H:%M:%S')
                
                print(f'[{time_str}] [{channel}]')
                try:
                    parsed_data = json.loads(data)
                    print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
                except:
                    print(data)
                print('-' * 40)
    except KeyboardInterrupt:
        print('Monitor stopped.')
        sys.exit(0)

if __name__ == '__main__':
    run_monitor()
