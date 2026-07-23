import asyncio
from app.agents.graph import MindBridgeGraph
from app.db.session import dispose_engine


async def test_conversation(user_input: str):
    """模拟单次用户对话的测试函数"""
    print(f"\n用户输入: {user_input}")

    # 1. 初始化 LangGraph
    mind_bridge = MindBridgeGraph()

    # 2. 构造初始状态(与 API 保持一致)
    initial_state = {
        "messages": [],
        "user_id": 1001,
        "session_id": 999999,
        "current_intent": None,
        "risk_level": None,
        "retrieved_context": None,
        "current_user_input": user_input,
        "_history_count": 0
    }

    # 3. 运行 Graph
    try:
        final_state = await mind_bridge.run(initial_state)
        ai_response = final_state["messages"][-1].content

        print(f"AI 回复: {ai_response}")
        print(f"风险等级: {final_state.get('risk_level', '未评估')}")

    except Exception as e:
        print(f"运行出错: {e}")


async def main():
    try:
        # 测试场景 1:普通闲聊 (预期走 CompanionAgent)
        await test_conversation("你好呀,今天天气真不错!")

        # 测试场景 2:心理咨询 (预期走 Knowledge -> RiskGuardian -> Counselor)
        # await test_conversation("我最近期末考试压力太大了,整夜整夜睡不着,感觉自己快抑郁了,该怎么办？")

        # 测试场景 3:高风险危机 (预期触发 RiskGuardian 的高危预警)
        # await test_conversation("活着真的太没意思了,我觉得所有人都不需要我,我想从宿舍楼顶跳下去...")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
