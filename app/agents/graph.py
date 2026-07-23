from typing import Any
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from langgraph.graph.state import CompiledStateGraph

# 导入我们编写的所有节点
from app.agents.nodes.memory import save_memory_node
from app.agents.nodes.parallel_init import parallel_init_node
from app.agents.nodes.knowledge import knowledge_node
from app.agents.nodes.risk_guardian import risk_guardian_node
from app.agents.nodes.companion import companion_node
from app.agents.nodes.counselor import counselor_node


class MindBridgeGraph:
    def __init__(self) -> None:
        self.graph: CompiledStateGraph = self._build_graph()

    @staticmethod
    def _build_graph() -> CompiledStateGraph:
        # 1. 初始化状态图
        # noinspection PyTypeChecker
        graph = StateGraph(AgentState)

        # 2. 注册所有节点
        # noinspection PyTypeChecker
        graph.add_node("parallel_init", parallel_init_node)  # 并行执行 supervisor + memory
        # noinspection PyTypeChecker
        graph.add_node("save_memory", save_memory_node)
        # noinspection PyTypeChecker
        graph.add_node("knowledge", knowledge_node)
        # noinspection PyTypeChecker
        graph.add_node("risk_guardian", risk_guardian_node)
        # noinspection PyTypeChecker
        graph.add_node("companion", companion_node)
        # noinspection PyTypeChecker
        graph.add_node("counselor", counselor_node)

        # 3. 定义边与流转规则 (Edges)
        # 入口:parallel_init(并行执行意图识别 + 历史加载,节省 30% 时间)
        graph.set_entry_point("parallel_init")

        # parallel_init 之后根据意图分流
        def _route_after_init(state: AgentState) -> str:
            intent = state.get("current_intent", "chat")
            if intent == "chat":
                return "companion"
            return "knowledge"

        graph.add_conditional_edges(
            "parallel_init",
            _route_after_init,
            {"companion": "companion", "knowledge": "knowledge"},
        )

        # chat 链路:companion → save_memory → END
        graph.add_edge("companion", "save_memory")

        # support 链路:knowledge → risk_guardian → counselor → save_memory → END
        graph.add_edge("knowledge", "risk_guardian")
        graph.add_edge("risk_guardian", "counselor")
        graph.add_edge("counselor", "save_memory")
        graph.add_edge("save_memory", END)

        # 4. 编译图
        return graph.compile()

    async def run(self, initial_state: dict[str, Any] | AgentState) -> dict[str, Any]:
        """
        暴露给外部调用的运行接口.
        """
        result = await self.graph.ainvoke(initial_state)
        return result
