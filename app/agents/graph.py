from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from langgraph.graph.state import CompiledStateGraph

# 导入我们编写的所有节点
from app.agents.nodes.memory import memory_node, save_memory_node
from app.agents.nodes.supervisor import supervisor_node
from app.agents.nodes.knowledge import knowledge_node
from app.agents.nodes.risk_guardian import risk_guardian_node
from app.agents.nodes.companion import companion_node
from app.agents.nodes.counselor import counselor_node


def _route_after_supervisor(state: AgentState) -> str:
    intent = state.get("current_intent", "chat")
    print(f"[Router] 意图 '{intent}' 触发路由流转...")

    if intent == "chat":
        return "chat"
    # 兜底：所有非 chat 的意图都走 support
    return "support"


class MindBridgeGraph:
    def __init__(self):
        self.graph: CompiledStateGraph = self._build_graph()

    @staticmethod
    def _build_graph() -> CompiledStateGraph:
        # 1. 初始化状态图
        # noinspection PyTypeChecker
        graph = StateGraph(AgentState)

        # 2. 注册所有节点
        # noinspection PyTypeChecker
        graph.add_node("memory", memory_node)
        # noinspection PyTypeChecker
        graph.add_node("save_memory", save_memory_node)
        # noinspection PyTypeChecker
        graph.add_node("supervisor", supervisor_node)
        # noinspection PyTypeChecker
        graph.add_node("knowledge", knowledge_node)
        # noinspection PyTypeChecker
        graph.add_node("risk_guardian", risk_guardian_node)
        # noinspection PyTypeChecker
        graph.add_node("companion", companion_node)
        # noinspection PyTypeChecker
        graph.add_node("counselor", counselor_node)

        # 3. 定义边与流转规则 (Edges)
        # 设置图的入口点
        graph.set_entry_point("memory")

        # 固定流转：记忆加载完成后，必然进入主管节点
        graph.add_edge("memory", "supervisor")

        # 条件流转（核心路由）
        graph.add_conditional_edges(
            "supervisor",
            _route_after_supervisor,
            {"chat": "companion", "support": "knowledge"},
        )

        # 深度处理链路的固定流转：知识检索 -> 风险风控 -> 心理咨询师
        graph.add_edge("knowledge", "risk_guardian")
        graph.add_edge("risk_guardian", "counselor")

        # 终端节点：处理完毕后，流程结束
        graph.add_edge("companion", "save_memory")
        graph.add_edge("counselor", "save_memory")
        graph.add_edge("save_memory", END)

        # 4. 编译图
        return graph.compile()

    async def run(self, initial_state: dict | AgentState):
        """
        暴露给外部调用的运行接口。
        """
        result = await self.graph.ainvoke(initial_state)
        return result
