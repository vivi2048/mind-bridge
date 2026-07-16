from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


# --- 1. 定义请求模型 ---
class ChatRequest(BaseModel):
    user_id: int
    session_id: int
    message: str


# --- 2. 挂载路由 ---
@router.post("/chat")
async def chat_endpoint(request: Request, chat_req: ChatRequest):
    """
    对话接口
    """
    try:
        # 1. 初始化图 (注意：这里应该使用单例或依赖注入，不要每次都重新初始化)
        # 提示：你可以参考 test_graph.py 中的写法
        graph = request.app.state.graph

        # 2. 构建初始状态 (State)
        initial_state = {
            "user_id": chat_req.user_id,
            "session_id": chat_req.session_id,
            "current_intent": None,
            "risk_level": None,
            "risk_reason": None,
            "retrieved_context": None,
            "current_user_input": chat_req.message
        }

        # 3. 运行图
        # 注意：这里应该使用 ainvoke 或 run，取决于你的 MindBridgeGraph 实现
        final_state = await graph.run(initial_state)

        # 4. 返回结果
        return {
            "status": "success",
            "response": final_state["messages"][-1].content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
