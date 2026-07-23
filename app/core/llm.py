from langchain_openai import ChatOpenAI
from app.core.config import settings


def create_llm(temperature: float = 0) -> ChatOpenAI:
    """
    创建 LLM 实例
    
    Args:
        temperature: 温度参数,0 表示确定性输出,越高越随机
        
    Returns:
        ChatOpenAI 实例
    """
    return ChatOpenAI(
        model=settings.llm_model_id,
        api_key=settings.api_key,
        base_url=settings.base_url,
        temperature=temperature,
        request_timeout=60,  # 60秒超时,防止慢请求无限挂起占用资源
        extra_body={"enable_thinking": False},
    )


# 预创建的常用 LLM 实例
llm_default: ChatOpenAI = create_llm(temperature=0)      # 确定性输出(分类、评估)
llm_creative: ChatOpenAI = create_llm(temperature=0.7)   # 创意输出(对话、陪伴)
llm_balanced: ChatOpenAI = create_llm(temperature=0.5)   # 平衡输出(咨询、建议)
