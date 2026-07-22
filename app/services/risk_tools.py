import logging
from typing import TypedDict
from app.models.entities import RiskEvent, RiskLevel
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


class AlertPayload(TypedDict):
    """预警任务的数据结构"""
    user_id: int
    session_id: int
    risk_level: str
    last_message: str
    target: str  # 预警目标（辅导员/危机干预中心）,默认为 campus_crisis_center


async def send_alert(payload: AlertPayload):
    """
    风险预警工具:发送预警通知给辅导员/危机干预中心,并记录风险事件
    """
    # 2. 将预警记录写入数据库
    async with async_session_factory() as session:
        try:
            # 将字符串风险等级转换为枚举类型
            risk_level_str = payload.get("risk_level", "low")
            try:
                risk_level_enum = RiskLevel(risk_level_str)
            except ValueError:
                risk_level_enum = RiskLevel.LOW

            new_risk_event = RiskEvent(
                user_id=payload["user_id"],
                session_id=payload.get("session_id"),
                risk_level=risk_level_enum,
                trigger_reason=payload["last_message"]
            )

            # 添加到会话并提交事务
            session.add(new_risk_event)
            await session.commit()

            # 刷新对象以获取数据库自动生成的 ID
            await session.refresh(new_risk_event)

            logger.info(f"[RiskTools] 预警已记录, event_id={new_risk_event.id}, risk={payload.get('risk_level')}")

        except Exception as e:
            # 发生异常时回滚事务,防止脏数据
            await session.rollback()
            logger.error(f"[RiskTools] 预警记录写入数据库失败: {e}", exc_info=True)
            raise  # 向上抛出异常,以便 TaskQueue 捕获并进行重试逻辑


async def create_case(payload: AlertPayload):
    """风险干预工具:创建心理干预个案"""
    logger.info(f"[RiskTools] 干预个案已创建, user_id={payload['user_id']}")


# 工具注册表,方便 Worker 动态调用
RISK_TOOL_REGISTRY = {
    "send_alert": send_alert,
    "create_case": create_case,
}
