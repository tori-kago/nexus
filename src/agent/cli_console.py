import asyncio
import requests
import websockets
import json
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from src.shared.schemas import NexusEnvelope, MessageType

console = Console()

async def listen_to_nexus():
    url = 'ws://localhost:8000/ws'
    try:
        async with websockets.connect(url) as websocket:
            while True:
                message = await websocket.recv()
                try:
                    # 按照 NUP v1.0 解析封包
                    envelope_data = json.loads(message)
                    payload = envelope_data.get('payload', {})
                    text = payload.get('content', str(payload))
                    trace_id = envelope_data.get('trace_id', 'unknown')
                    
                    # 呈現給用戶，將 trace_id 縮小顯示在邊角
                    console.print(Panel(
                        Markdown(text), 
                        title='Nexus', 
                        subtitle=f'trace: {trace_id[:8]}',
                        border_style='cyan'
                    ))
                except Exception as e:
                    console.print(Panel(f"Error parsing: {e}\nRaw: {message}", title='Nexus (Raw Error)', border_style='red'))
    except Exception as e:
        console.print(f'[red]WebSocket Error: {e}[/red]')

def send_input(msg):
    try:
        # 對齊 Gateway 期望的欄位: content
        payload = {
            'content': msg,
            'platform': 'cli_console',
            'user': 'maocao'
        }
        requests.post('http://localhost:8000/input', json=payload)
    except Exception as e:
        console.print(f'[red]Send Error: {e}[/red]')

async def main():
    console.print(Panel('[bold green]Nexus CLI Console (NUP v1.0)[/bold green]', title='System'))
    
    # 啟動 WebSocket 監聽任務
    listener_task = asyncio.create_task(listen_to_nexus())
    
    while True:
        try:
            # 由於 Prompt.ask 是阻塞的，我們放在 thread 執行
            user_input = await asyncio.to_thread(Prompt.ask, '[bold yellow]You[/bold yellow]')
            if user_input.lower() in ['exit', 'quit']: break
            send_input(user_input)
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            
    listener_task.cancel()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
