from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone
import enum


# 所有数据库实体都将继承这个基类
class Base(DeclarativeBase):
    pass


# --- 枚举定义 ---
class IntentType(str, enum.Enum):
    """SupervisorAgent 路由的三类意图"""
    CHAT = "chat"  # 普通聊天
    CONSULT = "consult"  # 心理咨询 (触发 RAG)
    RISK = "risk"  # 风险场景 (触发 RAG + 风险干预)


class RiskLevel(str, enum.Enum):
    """RiskGuardianAgent 评估的风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # 极高风险，需立即人工介入


class AlertStatus(str, enum.Enum):
    """预警闭环状态"""
    PENDING = "pending"  # 待发送
    SENT = "sent"  # 已发送
    CONFIRMED = "confirmed"  # 已确认接收
    INTERVENED = "intervened"  # 已人工干预


class TaskStatus(str, enum.Enum):
    """异步任务队列状态"""
    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    SUCCESS = "success"  # 执行成功
    FAILED = "failed"  # 执行失败
    DEAD_LETTER = "dead_letter"  # 进入死信队列


# --- 1. 用户账户表 (学生/咨询师/管理员) ---
class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名/学号")
    hashed_password = Column(String(255), nullable=False, comment="加密后的密码")
    role = Column(String(20), default="student", nullable=False, comment="角色: student/counselor/admin")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), comment="创建时间")

    # 关联关系
    sessions = relationship("ChatSession", back_populates="user")
    risk_events = relationship("RiskEvent", back_populates="user")


# --- 2. 对话会话表 (支撑 MemoryAgent) ---
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, comment="所属用户ID")
    title = Column(String(255), nullable=True, comment="会话标题(可由AI自动生成)")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc),
                        comment="最后更新时间")

    # 关联关系
    user = relationship("UserAccount", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


# --- 3. 对话消息表 (支撑流式对话与上下文) ---
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="消息ID")
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, comment="所属会话ID")
    role = Column(String(10), nullable=False, comment="角色: user / assistant / system")
    content = Column(Text, nullable=False, comment="消息内容")
    intent = Column(SAEnum(IntentType), nullable=True, comment="SupervisorAgent 识别的意图")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), comment="创建时间")

    # 关联关系
    session = relationship("ChatSession", back_populates="messages")


# --- 4. 风险事件表 (支撑 RiskGuardianAgent) ---
class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="风险事件ID")
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, comment="触发风险的用户ID")
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True, comment="触发风险的会话ID")
    risk_level = Column(SAEnum(RiskLevel), nullable=False, comment="风险等级")
    trigger_reason = Column(Text, nullable=False, comment="触发原因/AI分析摘要")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), comment="触发时间")

    # 关联关系
    user = relationship("UserAccount", back_populates="risk_events")
    alerts = relationship("AlertRecord", back_populates="risk_event", cascade="all, delete-orphan")


# --- 5. 预警闭环记录表 ---
class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="预警记录ID")
    risk_event_id = Column(Integer, ForeignKey("risk_events.id"), nullable=False, comment="关联的风险事件ID")
    status = Column(SAEnum(AlertStatus), default=AlertStatus.PENDING, nullable=False, comment="预警状态")
    sent_at = Column(DateTime, nullable=True, comment="发送时间")
    confirmed_at = Column(DateTime, nullable=True, comment="确认接收时间")
    intervention_notes = Column(Text, nullable=True, comment="干预备注/处理记录")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), comment="创建时间")

    # 关联关系
    risk_event = relationship("RiskEvent", back_populates="alerts")


# --- 6. 异步任务队列记录表 (支撑 MCP 工具与死信队列) ---
class AsyncTask(Base):
    __tablename__ = "async_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="任务ID")
    task_type = Column(String(50), nullable=False, comment="任务类型: create_case/send_alert/append_note")
    payload = Column(JSON, nullable=False, comment="任务参数(JSON)")
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, comment="任务状态")
    retry_count = Column(Integer, default=0, comment="重试次数")
    error_message = Column(Text, nullable=True, comment="最后一次失败的错误信息")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc),
                        comment="更新时间")
