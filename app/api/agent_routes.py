"""
Agent API 路由
"""
import json
import asyncio
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from app.agent.react_agent import react_agent
from app.tools.registry import tool_registry

router = APIRouter(prefix="/agent", tags=["Agent"])


# ========== 数据模型 ==========

class AgentQuery(BaseModel):
    question: str
    session_id: Optional[str] = None


class ToolInfo(BaseModel):
    name: str
    description: str


# ========== API 路由 ==========

@router.post("/chat")
async def agent_chat_stream(query: AgentQuery):
    """Agent 流式对话接口"""

    async def generate():
        yield f"data: {json.dumps({'type': 'session', 'session_id': query.session_id or 'default'})}\n\n"

        try:
            print(f"📝 收到问题: {query.question}")
            result = await asyncio.to_thread(react_agent.run, query.question)
            print(f"📦 Agent 返回: {result}")

            if not isinstance(result, dict):
                raise ValueError(f"Agent 返回类型错误: {type(result)}")

            steps = result.get("steps", [])

            for step in steps:
                thought = step.get('thought', '')
                action = step.get('action')
                action_input = step.get('action_input', '')
                observation = step.get('observation')

                if thought:
                    text = f"🤔 思考: {thought}\n"
                    yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"
                    await asyncio.sleep(0.05)

                if action:
                    text = f"🔧 执行: {action}({action_input})\n"
                    yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"
                    await asyncio.sleep(0.05)

                if observation:
                    text = f"📋 结果: {observation}\n\n"
                    yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"
                    await asyncio.sleep(0.05)

            answer = result.get("answer", "抱歉，无法回答")
            text = f"\n✅ {answer}"
            yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"❌ Agent 错误:\n{error_detail}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """列出所有可用工具"""
    tools = []
    for name in tool_registry.list_tools():
        tool = tool_registry.get(name)
        tools.append(ToolInfo(name=tool.name, description=tool.description))
    return tools