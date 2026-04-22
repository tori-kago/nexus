import asyncio
import os
import json
import logging
import requests
from datetime import datetime
from src.core.orchestrator import NexusOrchestrator
from src.adapters.brain.gemini_cli_adapter import GeminiCLIBrainAdapter
from src.adapters.memory.vault_adapter import VaultAdapter
from src.adapters.tool.python_tool_adapter import PythonToolAdapter
from src.core.session_store import SessionStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Nexus.Heartbeat")

GATEWAY_BASE_URL = "http://localhost:8000"

async def check_proactive_thought():
    """
    執行一次「靜默反思」，決定是否需要主動聯絡用戶。
    """
    brain = GeminiCLIBrainAdapter()
    memory = VaultAdapter()
    store = SessionStore()
    
    # 獲取最近活躍的會話 (過去 24 小時)
    active_sessions = store.get_active_sessions(hours=24)
    
    for session in active_sessions:
        sid = session["session_id"]
        platform = session["platform"]
        
        if not sid or not platform: continue
        
        current_time = datetime.now().strftime("%H:%M")
        logger.info(f"--- Proactive Check for {sid} ({platform}) at {current_time} ---")
        
        # 1. 建立「反思」Orchestrator
        # 在主動模式下，我們不提供 WebSocket 回調，因為這是靜默的
        orchestrator = NexusOrchestrator(brain=brain, memory=memory)
        
        # 2. 注入特殊的系統指令進行「反思」
        # 我們不使用 run() 而是直接呼叫內部的推理，
        # 或者在 run 中加入 is_proactive 標誌
        proactive_prompt = f"[SYSTEM HEARTBEAT] 當前時間是 {current_time}。請檢查你的長期記憶與之前的對話，決定是否需要主動對用戶說一句話。可能是關懷、提醒、或是對之前話題的補充。如果不需要，請輸出 IGNORE。"
        
        try:
            # 傳入 session 歷史，讓大腦有脈絡
            history = store.get_messages(sid)
            
            # 使用 wait_for 防止大腦反思太久
            reply = await asyncio.wait_for(
                orchestrator.run(proactive_prompt, is_proactive=True, session_context=history, session_id=sid),
                timeout=60.0
            )
            
            # 3. 處理決策
            if reply and "IGNORE" not in reply:
                logger.info(f"[*] Nexus decided to speak to {sid}: {reply[:30]}...")
                # 透過 Gateway 主動推播
                requests.post(f"{GATEWAY_BASE_URL}/notify", json={
                    "session_id": sid,
                    "content": reply
                })
            else:
                logger.info(f"[-] Nexus decided to remain silent for {sid}.")
                
        except Exception as e:
            logger.error(f"Error during heartbeat for {sid}: {e}")

async def main_loop():
    logger.info("Nexus Heartbeat Driver Started.")
    while True:
        await check_proactive_thought()
        # 每隔 1 小時反思一次 (可根據需求縮短，例如 30 分鐘)
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main_loop())
