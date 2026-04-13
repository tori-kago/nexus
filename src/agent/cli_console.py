import asyncio
import requests
import websockets
import json
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()

async def listen_to_nexus():
    url = 'ws://localhost:8000/ws'
    try:
        async with websockets.connect(url) as websocket:
            while True:
                message = await websocket.recv()
                try:
                    data = json.loads(message)
                    text = data.get('response', str(data))
                    console.print(Panel(Markdown(text), title='Nexus', border_style='cyan'))
                except:
                    console.print(Panel(message, title='Nexus (Raw)', border_style='cyan'))
    except Exception as e:
        console.print(f'[red]WebSocket Error: {e}[/red]')

def send_input(msg):
    try:
        requests.post('http://localhost:8000/input', json={'user': 'maocao', 'message': msg, 'type': 'text'})
    except Exception as e:
        console.print(f'[red]Send Error: {e}[/red]')

async def main():
    console.print(Panel('[bold green]Nexus CLI Console[/bold green]', title='System'))
    asyncio.create_task(listen_to_nexus())
    while True:
        try:
            user_input = await asyncio.to_thread(Prompt.ask, '[bold yellow]You[/bold yellow]')
            if user_input.lower() in ['exit', 'quit']: break
            send_input(user_input)
        except EOFError:
            break

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
