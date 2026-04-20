import asyncio
import time
from src.shared.bus import MessageBus
from src.shared.schemas import NexusEnvelope, MessageType

async def run_heartbeat():
    bus = MessageBus()
    print("[Heartbeat] Started. Emitting every 5 minutes...")
    
    while True:
        try:
            envelope = NexusEnvelope(
                source="system:heartbeat",
                type=MessageType.HEARTBEAT,
                trace_id=f"heartbeat-{int(time.time())}",
                payload={"status": "tick", "timestamp": time.time()}
            )
            bus.publish_envelope(envelope)
            print(f"[Heartbeat] 💓 Tick at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[Heartbeat] Error: {e}")
            
        await asyncio.sleep(300) # 5 mins

if __name__ == "__main__":
    asyncio.run(run_heartbeat())
