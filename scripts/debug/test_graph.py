import asyncio
from langchain_core.messages import HumanMessage
from app.agents.graph import MindBridgeGraph
from app.db.session import async_engine


async def test_conversation(user_input: str):
    """
    模拟单次用户对话的测试函数
    """
    print("\n" + "=" * 50)
    print(f"[用户输入]: {user_input}")
    print("=" * 50)

    # 1. 初始化 LangGraph
    mind_bridge = MindBridgeGraph()

    # 2. 构造初始状态
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_id": 1001,
        "session_id": 100101,
        "current_intent": None,
        "risk_level": None,
        "risk_reason": None,
        "retrieved_context": None,
        "final_response": None
    }

    # 3. 运行 Graph
    try:
        final_state = await mind_bridge.run(initial_state)

        # 4. 提取并打印最终回复
        ai_response = final_state["messages"][-1].content

        print("\n" + "-" * 50)
        print(f"[AI 最终回复]: {ai_response}")
        print(f"[最终风险等级]: {final_state.get('risk_level', '未评估')}")
        print("-" * 50 + "\n")

    except Exception as e:
        print(f"[测试运行出错]: {e}")


async def main():
    try:
        # 测试场景 1：普通闲聊 (预期走 CompanionAgent)
        await test_conversation("你好呀，今天天气真不错！")

        # 测试场景 2：心理咨询 (预期走 Knowledge -> RiskGuardian -> Counselor)
        # await test_conversation("我最近期末考试压力太大了，整夜整夜睡不着，感觉自己快抑郁了，该怎么办？")

        # 测试场景 3：高风险危机 (预期触发 RiskGuardian 的高危预警)
        # await test_conversation("活着真的太没意思了，我觉得所有人都不需要我，我想从宿舍楼顶跳下去...")
    finally:
        # 显式关闭数据库连接池，防止 GC 销毁时触发 Event loop is closed 警告
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
