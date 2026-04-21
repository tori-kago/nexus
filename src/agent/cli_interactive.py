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
BASE_URL = "http://localhost:8000"

def play_audio(url: str):
    try:
        full_url = BASE_URL + url
        temp_file = "temp_reply.mp3"
        r = requests.get(full_url)
        with open(temp_file, "wb") as f: f.write(r.content)
        
        # 非阻塞播放 (Linux/Mac 預設)
        if os.name == "nt":
            subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_file])
        else:
            for player in ["ffplay", "mpg123", "afplay"]:
                try:
                    cmd = [player, "-nodisp", "-autoexit", "-loglevel", "quiet", temp_file] if player == "ffplay" else [player, temp_file]
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    break
                except: continue
    except: pass

async def interactive_chat():
    url = "ws://localhost:8000/ws"
    console.print(Panel("[bold green]Nexus Flow CLI (v3.7)[/bold green]"))
    
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
                                live.update(Text(f"[{data.get('state').upper()}] {data.get('content')[:100]}", style="yellow"))
                                
                            elif data.get("type") == "text":
                                # 立即顯示文字，不等待音訊
                                live.update(Text(""))
                                console.print(f"[bold magenta]Nexus ({data.get('emotion')}) >[/bold magenta] {data.get('content')}")
                                
                            elif data.get("type") == "audio":
                                # 音訊隨後就到
                                play_audio(data.get("audio_url"))
                                break # 這一輪對話結束
                        except: break
                            
    except Exception as e:
        console.print(f"[bold red]連線失敗: {e}[/bold red]")

if __name__ == "__main__":
    try: asyncio.run(interactive_chat())
    except KeyboardInterrupt: pass
