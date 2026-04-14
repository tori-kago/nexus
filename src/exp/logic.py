import re

class ExpressionEngine:
    def process(self, text: str):
        """從文字中提取情緒標籤與表現指令"""
        # 1. 提取括號內的情緒標籤, 例如 (微笑), [思考]
        emotions = re.findall(r"[\(\[](.*?)[\)\]]", text)
        
        commands = []
        for em in emotions:
            # 濾掉明顯不是情緒的內容 (例如 [REFLECT] 標記在 Brain 層處理，這裡可以選擇忽略)
            if em.startswith("REFLECT:"):
                continue
                
            commands.append({"type": "expression", "value": em})
            
        return commands
