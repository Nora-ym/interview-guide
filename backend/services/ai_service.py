"""
====================================================
AI / LLM 统一服务
====================================================
这个文件封装了所有与大模型交互的逻辑，包括：
1. 普通对话（chat）：发送消息，等待完整回复
2. 流式对话（chat_stream）：逐字返回，用于打字机效果
3. 结构化输出（chat_structured）：让大模型返回 JSON 格式
4. 文本向量化（embed_texts / embed_query）：把文本转成数字向量

为什么统一封装？
    - 如果以后要换模型（从千问换成 GPT-4），只改这个文件
    - 所有调用方不需要关心底层用什么模型
    - 统一管理 API Key、温度、token 限制等参数

技术细节：
    DashScope（阿里云百炼）提供了兼容 OpenAI 的 API 格式，
    所以可以用 LangChain 的 OpenAI 集成来调用 DashScope 模型。
    只需要把 base_url 改成 DashScope 的地址就行。
"""

import json
from typing import AsyncIterator

# LangChain 组件
from langchain_openai import ChatOpenAI        # 大语言模型客户端
from langchain_openai import OpenAIEmbeddings   # 向量化模型客户端
from langchain_core.messages import (             # 消息类型
    HumanMessage,    # 用户消息
    SystemMessage,   # 系统提示词
    AIMessage,       # AI 回复
)

from backend.config import get_settings

settings = get_settings()


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """
    获取大语言模型客户端

    参数：
        temperature：温度参数（0-2）
            - 0：最确定，每次回答基本一样（适合代码、分析）
            - 0.7：有一定随机性（适合聊天）
            - 2：很随机，可能胡说八道（一般不用）

    优先使用 DashScope（阿里云），如果没配置 API Key 则用 OpenAI
    """
    # 决定用哪个平台
    api_key = settings.dashscope_api_key or settings.openai_api_key
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = settings.dashscope_chat_model

    # 如果配了 OpenAI 但没配 DashScope，用 OpenAI
    if settings.openai_api_key and not settings.dashscope_api_key:
        base_url = settings.openai_api_base
        model = settings.openai_chat_model

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=4096,
        timeout=120,
    )


def get_embeddings() -> OpenAIEmbeddings:
    """
    获取向量化模型客户端

    向量化模型的作用：把一段文字转成一个固定长度的数字数组
    例如："Java 是一门编程语言" → [0.12, -0.34, 0.56, ..., 0.78]（1536 个数字）
    语义相近的文本，向量也相近（通过余弦相似度计算）
    """
    api_key = settings.dashscope_api_key or settings.openai_api_key
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = settings.dashscope_embedding_model

    if settings.openai_api_key and not settings.dashscope_api_key:
        base_url = settings.openai_api_base
        model = settings.openai_embedding_model

    return OpenAIEmbeddings(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


async def chat(
    messages: list[dict],
    temperature: float = 0.7,
    system_prompt: str = "",
) -> str:
    """
    普通对话：发送消息，等待完整回复

    参数：
        messages: 对话历史，格式 [{"role": "user/assistant", "content": "..."}]
        temperature: 温度
        system_prompt: 系统提示词（告诉大模型它的角色和行为规则）

    返回：
        大模型的回复文本
    """
    llm = get_llm(temperature=temperature)

    # 构建 LangChain 消息列表
    lc_messages = []

    # 1. 系统提示词（如果有的话）
    if system_prompt:
        lc_messages.append(SystemMessage(content=system_prompt))

    # 2. 对话历史
    for msg in messages:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    # 3. 调用大模型
    response = await llm.ainvoke(lc_messages)
    return response.content


async def chat_stream(
    messages: list[dict],
    temperature: float = 0.7,
    system_prompt: str = "",
) -> AsyncIterator[str]:
    """
    流式对话：逐 token 返回（打字机效果）

    与 chat() 的区别：
    - chat()：等大模型全部生成完才返回（可能等 30 秒）
    - chat_stream()：大模型每生成几个字就立即返回

    前端配合 SSE（Server-Sent Events）实现打字机效果。

    返回：
        异步迭代器，每次 yield 一小段文本
    """
    llm = get_llm(temperature=temperature)

    lc_messages = []
    if system_prompt:
        lc_messages.append(SystemMessage(content=system_prompt))

    for msg in messages:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    # astream：异步流式调用，每次返回一小块
    async for chunk in llm.astream(lc_messages):
        yield chunk.content


async def chat_structured(
    messages: list[dict],
    output_schema: dict,
    temperature: float = 0.3,
    system_prompt: str = "",
) -> dict:
    """
    结构化输出：让大模型返回 JSON 格式

    大模型默认返回自然语言文本，但我们有时需要它返回结构化的 JSON。
    例如：让大模型评估简历，返回 {"score": 85, "strengths": [...]}

    实现原理：
    在 system_prompt 中放一个 JSON 模板，要求大模型严格按格式返回，
    然后我们把返回的文本解析成 Python 字典。

    参数：
        messages: 对话历史
        output_schema: 期望的 JSON 格式（作为示例给大模型看）
        temperature: 较低温度（0.3），让输出更稳定
        system_prompt: 系统提示词

    返回：
        解析后的 Python 字典
    """
    # 构建格式要求指令
    schema_instruction = f"""
请严格按照以下 JSON 格式返回结果，不要包含任何额外文字说明：

{json.dumps(output_schema, ensure_ascii=False, indent=2)}

只返回 JSON，不要用 markdown 代码块包裹。
"""
    # 拼接系统提示词
    full_system = system_prompt + "\n\n" + schema_instruction

    # 调用普通对话
    result = await chat(messages, temperature=temperature, system_prompt=full_system)

    # 清理返回结果（大模型有时会包裹 markdown 代码块，需要去掉）
    result = result.strip()
    for prefix in ["```json", "```"]:
        if result.startswith(prefix):
            result = result[len(prefix):]
    if result.endswith("```"):
        result = result[:-3]
    result = result.strip()

    # 解析 JSON
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"error": "结构化输出解析失败", "raw": result}


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    批量文本向量化

    把多段文本转成向量（数字数组）。
    用于 RAG 知识库：把文档分块后的每一段文本都向量化存储。

    参数：
        texts: 文本列表，如 ["第一段", "第二段", "第三段"]

    返回：
        向量列表，如 [[0.1, 0.2, ...], [0.3, 0.4, ...], ...]
        每个向量是一个有 1536 个浮点数的列表
    """
    embeddings = get_embeddings()
    return await embeddings.aembed_documents(texts)


async def embed_query(text: str) -> list[float]:
    """
    单条文本向量化（查询用）

    和 embed_texts 的区别：
    - embed_texts：批量向量化（文档分块时用）
    - embed_query：单条向量化（用户提问时用）

    参数：
        text: 一段文本，如 "什么是微服务？"

    返回：
        向量，如 [0.1, 0.2, ..., 0.9]（1536 个浮点数）
    """
    embeddings = get_embeddings()
    return await embeddings.aembed_query(text)