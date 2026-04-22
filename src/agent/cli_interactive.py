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
    console.print(Panel("[bold green]Nexus Deep Reasoning CLI (v5.1.1)[/bold green]"))
    
    try:
        async with websockets.connect(url) as websocket:
            while True:
                user_input = console.input("\n[bold cyan]You > [/bold cyan]")
                if user_input.lower() in ["exit", "quit", "bye"]: break
                if not user_input.strip(): continue
                
                await websocket.send(json.dumps({"content": user_input}))
                
                with Live(Text("Nexus 正在啟動大腦..."), refresh_per_second=4, transient=True) as live:
                    while True:
                        try:
                            # 增加逾時到 300 秒 (5分鐘)
                            response = await asyncio.wait_for(websocket.recv(), timeout=300.0)
                            data = json.loads(response)
                            
                            if data.get("type") == "thought":
                                state = data.get('state', '').upper()
                                content = data.get('content', '')
                                live.update(Text(f"[{state}] {content[:150]}", style="yellow"))
                                
                            elif data.get("type") == "text":
                                live.update(Text(""))
                                content = data.get('content')
                                emotion = data.get('emotion', 'neutral')
                                console.print(f"[bold magenta]Nexus ({emotion}) >[/bold magenta] {content}")
                                if not data.get("is_proactive"):
                                    break
                                
                            elif data.get("type") == "audio":
                                play_audio(data.get("audio_url"))
                                
                        except asyncio.TimeoutError:
                            console.print("[dim red](大腦還在努力思考中...)[/dim red]")
                        except Exception as e:
                            console.print(f"[bold red]通訊異常: {e}[/bold red]")
                            break
                            
    except Exception as e:
        console.print(f"[bold red]連線失敗: {e}[/bold red]")

if __name__ == "__main__":
    try: asyncio.run(interactive_chat())
    except KeyboardInterrupt: pass
