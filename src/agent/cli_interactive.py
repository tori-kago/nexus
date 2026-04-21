import asyncio
import websockets
import json
import os
import requests
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

console = Console()

# 基礎 URL 用於下載音訊
BASE_URL = "http://localhost:8000"

def play_audio(url: str):
    """
    下載並播放音訊。
    使用系統指令進行播放以簡化依賴。
    """
    try:
        full_url = BASE_URL + url
        temp_file = "temp_reply.mp3"
        
        # 下載檔案
        r = requests.get(full_url)
        with open(temp_file, "wb") as f:
            f.write(r.content)
            
        # 根據系統選擇播放器 (優先使用 ffplay，因為它通常隨 ffmpeg 安裝)
        # -nodisp: 不顯示視窗, -autoexit: 播放完自動退出
        if os.name == "nt": # Windows
            subprocess.run(["ffplay", "-nodisp", "-autoexit", temp_file], capture_output=True)
        else: # Linux / Mac
            # 嘗試 ffplay, mpg123, 或 macOS 的 afplay
            for player in ["ffplay", "mpg123", "afplay"]:
                try:
                    cmd = [player, "-nodisp", "-autoexit", temp_file] if player == "ffplay" else [player, temp_file]
                    subprocess.run(cmd, capture_output=True, check=True)
                    break
                except: continue
                
    except Exception as e:
        console.print(f"[dim red](播放失敗: {e})[/dim red]")

async def interactive_chat():
    url = "ws://localhost:8000/ws"
    console.print(Panel("[bold green]Nexus Voice CLI (v3.5)[/bold green]\n連接至 " + url))
    
    try:
        async with websockets.connect(url) as websocket:
            while True:
                user_input = console.input("\n[bold cyan]You > [/bold cyan]")
                if user_input.lower() in ["exit", "quit"]: break
                
                await websocket.send(json.dumps({"content": user_input}))
                
                with Live(Text("Nexus 正在思考..."), refresh_per_second=4, transient=True) as live:
                    while True:
                        try:
                            response = await websocket.recv()
                            data = json.loads(response)
                            
                            if data.get("type") == "thought":
                                state = data.get("state", "thinking")
                                content = data.get("content", "")
                                color = "yellow" if state == "thinking" else "blue"
                                live.update(Text(f"[{state.upper()}] {content}", style=color))
                                
                            elif data.get("type") == "text":
                                live.update(Text("")) 
                                content = data.get('content')
                                emotion = data.get('emotion', 'neutral')
                                console.print(f"[bold magenta]Nexus ({emotion}) >[/bold magenta] {content}")
                                
                                # 如果有音訊 URL，啟動播放
                                if data.get("audio_url"):
                                    # 這裡使用同步播放會阻塞下一輪輸入，若要不阻塞可用 asyncio.to_thread
                                    play_audio(data.get("audio_url"))
                                break
                        except: break
                            
    except Exception as e:
        console.print(Panel(f"[bold red]連線失敗: {e}[/bold red]", title="Error"))

if __name__ == "__main__":
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]已停止對話。[/bold yellow]")
