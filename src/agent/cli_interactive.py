import asyncio
import websockets
import json
import sys
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

console = Console()

async def interactive_chat():
    url = "ws://localhost:8000/ws"
    
    console.print(Panel("[bold green]Nexus Autonomous CLI (v3.0)[/bold green]\n連接至 " + url))
    
    try:
        async with websockets.connect(url) as websocket:
            while True:
                # 1. 獲取用戶輸入
                user_input = console.input("\n[bold cyan]You > [/bold cyan]")
                if user_input.lower() in ["exit", "quit", "bye"]:
                    break
                
                # 2. 發送至 WebSocket
                await websocket.send(json.dumps({"content": user_input}))
                
                # 3. 接收流式回饋
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
                                # 最終回覆
                                live.update(Text("")) # 清除 live 內容
                                console.print(f"[bold magenta]Nexus >[/bold magenta] {data.get('content')}")
                                break
                                
                        except Exception as e:
                            console.print(f"[bold red]接收錯誤: {e}[/bold red]")
                            break
                            
    except Exception as e:
        console.print(Panel(f"[bold red]連線失敗: {e}[/bold red]\n請確保已啟動 python3 src/gateway/main.py", title="Error"))

if __name__ == "__main__":
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]已停止對話。[/bold yellow]")
