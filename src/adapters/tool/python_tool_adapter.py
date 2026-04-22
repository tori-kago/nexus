import asyncio
import json
import inspect
import time
import os
import importlib.util
from typing import Dict, Any, Callable, Optional, List, Type, get_type_hints
from pydantic import BaseModel, Field, create_model, ValidationError

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    param_model: Optional[Type[BaseModel]] = None

class PythonToolAdapter:
    """
    Python 函數工具適配器 3.1 (Adaptive Unpacking)。
    具備參數自動解包能力，防止大腦傳入過度包裝的 JSON。
    """
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
        self.custom_skills_path = "src/skills"

    def register_tool(self, name: str, description: str, func: Callable):
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        fields = {}
        properties = {}
        required = []
        for p_name, p in sig.parameters.items():
            p_type = type_hints.get(p_name, Any)
            fields[p_name] = (p_type, ... if p.default == inspect.Parameter.empty else p.default)
            properties[p_name] = {"type": "string", "description": f"參數 {p_name}"}
            if p.default == inspect.Parameter.empty: required.append(p_name)
        
        dynamic_model = create_model(f"{name}_Params", **fields)
        self._tools[name] = func
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            parameters_schema={"type": "object", "properties": properties, "required": required},
            param_model=dynamic_model
        )
        print(f"[ToolHub] Registered: {name}")

    def load_custom_skills(self):
        # 暫時不實作複雜的動態載入，維持穩定
        pass

    async def execute(self, tool_name: str, params: Any) -> str:
        """
        執行工具，具備自適應解包邏輯。
        """
        if tool_name not in self._tools:
            return f"Error: Tool '{tool_name}' not found."
            
        func = self._tools[tool_name]
        definition = self._definitions[tool_name]
        
        # --- 核心邏輯：參數預處理 ---
        # 如果大腦傳來的是字串（例如 "ls -la"），但我們預期是字典
        if isinstance(params, str):
            try:
                # 嘗試解析為 JSON
                params = json.loads(params.replace("'", '"'))
            except:
                # 失敗則將字串包裝成第一個參數
                first_param_name = list(definition.param_model.__annotations__.keys())[0]
                params = {first_param_name: params}

        # 如果傳入的是字典，但裡面只有一個 key 且與函數參數名不符 (常見於大腦幻覺)
        # 例如: 傳入 {"command": "ls"} 給 run_shell(cmd)
        if isinstance(params, dict) and len(params) == 1:
            val = list(params.values())[0]
            param_key = list(params.keys())[0]
            expected_key = list(definition.param_model.__annotations__.keys())[0]
            if param_key != expected_key:
                # 自動修正 key
                params = {expected_key: val}

        try:
            # 參數驗證
            validated = definition.param_model(**params).model_dump()
            if asyncio.iscoroutinefunction(func):
                result = await func(**validated)
            else:
                result = func(**validated)
            return str(result)
        except ValidationError as ve:
            return f"參數錯誤: {ve.json()}"
        except Exception as e:
            return f"執行錯誤 ({tool_name}): {str(e)}"

    def get_system_prompt_fragment(self) -> str:
        if not self._definitions: return ""
        prompt = "## 可用工具清單 (Capabilities)\n"
        for d in self._definitions.values():
            prompt += f"- {d.name}: {d.description} (格式: {json.dumps(d.parameters_schema)})\n"
        return prompt
