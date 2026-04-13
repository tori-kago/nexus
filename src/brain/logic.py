from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, List
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from src.brain.factory import get_brain_model

# 1. 定義對話狀態 (State)
class AgentState(TypedDict):
    # 使用 operator.add 來累積歷史訊息 (簡易版記憶)
    messages: Annotated[List[BaseMessage], operator.add]

# 2. 定義模型處理節點 (Node)
class BrainLogic:
    def __init__(self):
        self.model = get_brain_model()

    def call_model(self, state: AgentState):
        messages = state['messages']
        response = self.model.invoke(messages)
        return {"messages": [response]}

# 3. 建立 LangGraph 圖表 (Graph)
def create_brain_graph():
    brain = BrainLogic()
    workflow = StateGraph(AgentState)
    
    # 添加唯一節點：思考
    workflow.add_node("think", brain.call_model)
    
    # 設定入口與出口
    workflow.add_edge(START, "think")
    workflow.add_edge("think", END)
    
    return workflow.compile()
