import asyncio
import logging
from app.agents.state import AgentState
from app.agents.nodes.supervisor import supervisor_node
from app.agents.nodes.memory import memory_node

logger = logging.getLogger(__name__)


async def parallel_init_node(state: AgentState) -> dict:
    """
    并行初始化节点:同时执行意图识别(supervisor)和历史加载(memory).
    这两个操作无数据依赖,可并行执行以节省约 30% 响应时间.
    """
    # 并行执行 supervisor 和 memory
    supervisor_result, memory_result = await asyncio.gather(
        supervisor_node(state),
        memory_node(state),
        return_exceptions=True
    )
    
    # 合并结果
    merged_state = {}
    
    # 处理 supervisor 结果
    if isinstance(supervisor_result, Exception):
        logger.error(f"[ParallelInit] supervisor 执行失败: {supervisor_result}")
        # 失败时默认路由到 chat
        merged_state["current_intent"] = "chat"
    else:
        merged_state.update(supervisor_result)
    
    # 处理 memory 结果
    if isinstance(memory_result, Exception):
        logger.error(f"[ParallelInit] memory 执行失败: {memory_result}")
        # 失败时只保留当前输入
        from langchain_core.messages import HumanMessage
        merged_state["messages"] = [HumanMessage(content=state.get("current_user_input", ""))]
        merged_state["_history_count"] = 0
    else:
        merged_state.update(memory_result)
    
    return merged_state
