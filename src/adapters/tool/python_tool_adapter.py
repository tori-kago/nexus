import asyncio
import json
import inspect
import time
from typing import Dict, Any, Callable, Optional, List, Type, get_type_hints
from pydantic import BaseModel, Field, create_model, ValidationError

class ToolResult(BaseModel):
    """標準化工具執行結果"""
    success: bool
    data: str
    error: Optional[str] = None
    execution_time: float = 0.0

class ToolDefinition(BaseModel):
    """工具的元數據定義"""
    name: str
    description: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    param_model: Optional[Type[BaseModel]] = None # 用於校驗的 Pydantic 模型

class PythonToolAdapter:
    """
    Python 函數工具適配器 2.2 (Ultra-Stable)。
    支援 Runtime 強型別校驗、自動 Schema 推導與執行結果標準化。
    """
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, ToolDefinition] = {}

    def register_tool(self, name: str, description: str, func: Callable):
        """
        註冊工具，並自動從函數的 Type Hints 推導 JSON Schema 與 Pydantic 校驗模型。
        """
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        fields = {}
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            param_type = type_hints.get(param_name, Any)
            
            # 1. 建立 Pydantic 欄位定義 (用於動態模型)
            default_val = ... if param.default == inspect.Parameter.empty else param.default
            fields[param_name] = (param_type, default_val)
            
            # 2. 建立 JSON Schema 說明 (用於 Prompt)
            type_str = "string"
            if param_type == int: type_str = "integer"
            elif param_type == float: type_str = "number"
            elif param_type == bool: type_str = "boolean"
            
            properties[param_name] = {
                "type": type_str,
                "description": f"參數 {param_name}"
            }
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        # 建立動態校驗模型
        dynamic_model = create_model(f"{name}_Params", **fields)

        definition = ToolDefinition(
            name=name,
            description=description,
            parameters_schema={
                "type": "object",
                "properties": properties,
                "required": required
            },
            param_model=dynamic_model
        )
        
        self._tools[name] = func
        self._definitions[name] = definition
        print(f"[ToolAdapter 2.2] Registered: {name} (Type-safe enabled)")

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        執行工具。包含參數校驗與錯誤捕捉。
        """
        if tool_name not in self._tools:
            return f"Error: Tool '{tool_name}' not found."
            
        start_time = time.time()
        definition = self._definitions[tool_name]
        
        try:
            # 1. 參數校驗 (Runtime Validation)
            if definition.param_model:
                try:
                    # 使用 Pydantic 自動進行轉型與驗證
                    validated_params = definition.param_model(**params).model_dump()
                except ValidationError as ve:
                    # 這是最關鍵的：給大腦清晰的錯誤指引
                    error_details = ve.errors()
                    err_msg = f"參數校驗失敗: {tool_name} 期待的參數格式不正確。\n"
                    for err in error_details:
                        err_msg += f"- 欄位 '{err['loc'][0]}': {err['msg']} (傳入值: {params.get(err['loc'][0])})\n"
                    return err_msg

            # 2. 執行函數
            func = self._tools[tool_name]
            if asyncio.iscoroutinefunction(func):
                result_data = await func(**validated_params)
            else:
                result_data = func(**validated_params)
            
            return str(result_data)
            
        except Exception as e:
            return f"執行錯誤 ({tool_name}): {str(e)}"

    def get_system_prompt_fragment(self) -> str:
        if not self._definitions:
            return "目前沒有可用的外部工具。"
            
        prompt = "## 可用工具與技能清單 (Capabilities)\n"
        prompt += "請嚴格遵守參數格式，若執行出錯，請根據 Observation 反思並修正參數後再次嘗試。\n\n"
        for def_obj in self._definitions.values():
            prompt += f"### {def_obj.name}\n"
            prompt += f"- **用途**: {def_obj.description}\n"
            prompt += f"- **參數規格**: {json.dumps(def_obj.parameters_schema, ensure_ascii=False, indent=2)}\n\n"
        return prompt
