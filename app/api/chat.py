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
            "messages": [],  # 空列表,memory_node 会填充历史消息
            "user_id": chat_req.user_id,
            "session_id": chat_req.session_id,
            "current_intent": None,
            "risk_level": None,
            "risk_reason": None,
            "retrieved_context": None,
            "current_user_input": chat_req.message,
            "_history_count": 0,
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        }

        async def generate():
            """生成流式响应"""
            total_token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            try:
                logger.info("开始执行 LangGraph")
                async for event in graph.graph.astream_events(initial_state, version="v2"):
                    kind = event.get("event")
                    metadata = event.get("metadata", {})
                    node_name = metadata.get("langgraph_node", "")
                    
                    # 捕获所有节点的 token 使用信息(累积)
                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        # 流式输出 token(仅来自 companion/counselor 节点)
                        if node_name in ["companion", "counselor"] and chunk and hasattr(chunk, 'content') and chunk.content:
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                        # 捕获 token 使用信息(所有节点)
                        if chunk and hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                            usage = chunk.usage_metadata
                            total_token_usage["input_tokens"] += usage.get("input_tokens", 0)
                            total_token_usage["output_tokens"] += usage.get("output_tokens", 0)
                            total_token_usage["total_tokens"] += usage.get("total_tokens", 0)
                    
                    elif kind == "on_chain_end":
                        if event.get("name") == "LangGraph":
                            final_state = event.get("data", {}).get("output", {})
                            logger.info(f"LangGraph 执行完成, risk_level={final_state.get('risk_level')}")
                            done_data = {
                                'type': 'done',
                                'risk_level': final_state.get('risk_level', 'unknown'),
                                'token_usage': total_token_usage
                            }
                            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
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

    except Exception as ex:
        logger.error(f"聊天接口异常: {ex}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误,请稍后重试")
