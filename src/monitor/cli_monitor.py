import redis
import json
import sys
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from collections import deque

# 假設 src/shared/schemas.py 已有 NexusEnvelope
# 為了避免在 Monitor 端引入過多依賴，我們直接解析 JSON 並依照 NUP 規格處理

console = Console()

class NexusMonitor:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.traces = {} # trace_id -> list of messages
        self.max_traces = 5
        self.trace_order = deque(maxlen=self.max_traces)

        self.type_styles = {
            "input": "bold green",
            "thought": "italic yellow",
            "text": "bold cyan",
            "command": "bold magenta",
            "system": "blue"
        }
        
        self.type_icons = {
            "input": "📥",
            "thought": "🧠",
            "text": "💬",
            "command": "🤖",
            "system": "⚙️"
        }

    def add_message(self, channel, data):
        try:
            msg = json.loads(data)
            trace_id = msg.get("trace_id", "unknown")
            msg_type = msg.get("type", "unknown")
            
            if trace_id not in self.traces:
                self.traces[trace_id] = []
                self.trace_order.append(trace_id)
            
            # 限制每個 trace_id 的訊息數量，避免內存過大
            self.traces[trace_id].append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "channel": channel,
                "type": msg_type,
                "source": msg.get("source", "unknown"),
                "payload": msg.get("payload", {})
            })
            
            # 清理過舊的 traces
            if len(self.trace_order) == self.max_traces:
                current_keys = list(self.traces.keys())
                for k in current_keys:
                    if k not in self.trace_order:
                        del self.traces[k]
        except Exception as e:
            console.print(f"[red]Error parsing message:[/red] {e}")

    def generate_display(self):
        table = Table(title="Nexus Pulse - Real-time Monitor", expand=True)
        table.add_column("Trace ID", style="dim", width=12)
        table.add_column("Flow (NUP Waterfall)", ratio=1)

        for tid in reversed(list(self.trace_order)):
            messages = self.traces.get(tid, [])
            flow_text = Text()
            
            for i, m in enumerate(messages):
                m_type = m['type']
                style = self.type_styles.get(m_type, "white")
                icon = self.type_icons.get(m_type, "❓")
                
                # 取得內容
                content = ""
                payload = m['payload']
                if m_type == "input":
                    content = payload.get("content", "")
                elif m_type == "thought":
                    content = payload.get("reasoning", payload.get("state", ""))
                elif m_type == "text":
                    content = payload.get("content", f"[{payload.get('emotion', 'neutral')}]")
                elif m_type == "command":
                    content = f"{payload.get('action')}({payload.get('params', {})})"
                else:
                    content = str(payload)

                # 格式化縮進
                prefix = "  └─ " if i > 0 else ""
                flow_text.append(f"{prefix}[{m['time']}] {icon} ", style=style)
                flow_text.append(f"{m['source']:<10} ", style="dim")
                flow_text.append(f"{content}\n", style=style)

            table.add_row(tid[:8] + "...", flow_text)
            table.add_section()
            
        return table

    def run(self):
        p = self.redis.pubsub()
        p.psubscribe('nexus.*')
        
        console.print(Panel("Nexus Monitor P0 Started\nListening on nexus.*", title="Status", border_style="green"))

        with Live(self.generate_display(), refresh_per_second=4) as live:
            try:
                for message in p.listen():
                    if message['type'] == 'pmessage':
                        self.add_message(message['channel'], message['data'])
                        live.update(self.generate_display())
            except KeyboardInterrupt:
                console.print("\n[yellow]Monitor stopped.[/yellow]")

if __name__ == "__main__":
    monitor = NexusMonitor()
    monitor.run()
