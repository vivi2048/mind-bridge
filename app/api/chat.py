import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from app.agents.state import AgentState

router = APIRouter()
logger = logging.getLogger(__name__)


# --- 1. 定义请求模型 ---
class ChatRequest(BaseModel):
    user_id: int
    session_id: int
    message: str


# --- 2. 挂载路由 ---
@router.post("/chat")
async def chat_endpoint(request: Request, chat_req: ChatRequest):
    """
    对话接口 - 流式响应
    """
    logger.info(f"收到聊天请求: user_id={chat_req.user_id}, session_id={chat_req.session_id}")
    
    try:
        graph = request.app.state.graph

        initial_state: AgentState = {
            "messages": [],  # 空列表，memory_node 会填充历史消息
            "user_id": chat_req.user_id,
            "session_id": chat_req.session_id,
            "current_intent": None,
            "risk_level": None,
            "risk_reason": None,
            "retrieved_context": None,
            "current_user_input": chat_req.message,
            "_history_count": 0
        }

        async def generate():
            """生成流式响应"""
            try:
                logger.info("开始执行 LangGraph")
                async for event in graph.graph.astream_events(initial_state, version="v2"):
                    kind = event.get("event")
                    metadata = event.get("metadata", {})
                    node_name = metadata.get("langgraph_node", "")
                    
                    if kind == "on_chat_model_stream" and node_name in ["companion", "counselor"]:
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, 'content') and chunk.content:
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                    
                    elif kind == "on_chain_end":
                        if event.get("name") == "LangGraph":
                            final_state = event.get("data", {}).get("output", {})
                            logger.info(f"LangGraph 执行完成, risk_level={final_state.get('risk_level')}")
                            yield f"data: {json.dumps({'type': 'done', 'risk_level': final_state.get('risk_level', 'unknown')}, ensure_ascii=False)}\n\n"
                            break

            except Exception as e:
                logger.error(f"流式响应生成失败: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        logger.error(f"聊天接口异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
