"""
RAG 核心引擎
整合：向量检索 + 对话历史 + LLM生成
"""
from typing import AsyncGenerator, Optional

from langchain_ollama import OllamaLLM

from app.config import settings
from app.core.vector_store import vector_manager
from app.core.chat_memory import ChatMemoryManager, format_history_for_prompt


class RAGEngine:
    """RAG 问答引擎"""

    def __init__(self, memory_manager: ChatMemoryManager):
        self.memory = memory_manager
        self.llm = OllamaLLM(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.7,
            num_predict=1024
        )
        self.retriever = vector_manager.get_retriever()

    def _build_prompt(
            self,
            question: str,
            context: str,
            history: str = ""
    ) -> str:
        """构建完整的 Prompt"""

        history_section = ""
        if history:
            history_section = f"""
历史对话（用于理解上下文）:
{history}
"""

        prompt = f"""你是"{settings.BOT_NAME}"，一个专业友好的AI助手，由{settings.BOT_COMPANY}开发。

身份规则：
- 你的名字是：{settings.BOT_NAME}
- 你的开发者是：{settings.BOT_COMPANY}
- 当被问到身份相关问题时，使用上述信息回答

回答规则：
1. 根据【知识库内容】回答问题
2. 如果知识库没有相关信息，诚实说"我不太清楚这个问题"
3. 保持友好、专业的语气
4. 回答要简洁明了
{history_section}
【知识库内容】:
{context}

【用户问题】: {question}

【回答】:"""

        return prompt

    async def ask(
            self,
            question: str,
            session_id: str
    ) -> tuple[str, list[str]]:
        """
        处理问题（非流式）
        返回：(答案, 来源列表)
        """
        # 1. 获取历史对话
        history_messages = await self.memory.get_history(session_id)
        history_text = format_history_for_prompt(history_messages)

        # 2. 检索相关文档
        docs = self.retriever.invoke(question)
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)

        # 3. 构建 prompt
        prompt = self._build_prompt(question, context, history_text)

        # 4. 调用 LLM
        answer = self.llm.invoke(prompt)

        # 5. 保存对话
        await self.memory.add_message(session_id, "human", question)
        await self.memory.add_message(session_id, "ai", answer)

        # 6. 提取来源
        sources = [
            f"[{doc.metadata.get('source', '未知')}] {doc.page_content[:80]}..."
            for doc in docs[:3]
        ]

        return answer, sources

    async def ask_stream(
            self,
            question: str,
            session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        流式问答
        """
        # 1. 获取历史对话
        history_messages = await self.memory.get_history(session_id)
        history_text = format_history_for_prompt(history_messages)

        # 2. 检索相关文档
        docs = self.retriever.invoke(question)
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)

        # 3. 构建 prompt
        prompt = self._build_prompt(question, context, history_text)

        # 4. 流式生成
        full_answer = ""
        for chunk in self.llm.stream(prompt):
            full_answer += chunk
            yield chunk

        # 5. 保存完整对话
        await self.memory.add_message(session_id, "human", question)
        await self.memory.add_message(session_id, "ai", full_answer)