"""
RAG 知识库工具 - 整合现有的 RAG 功能
"""
from app.tools.base import BaseTool, ToolResult
from app.core.vector_store import vector_manager


class RAGTool(BaseTool):
    """查询本地知识库"""

    name = "search_knowledge"
    description = "搜索本地知识库获取公司/产品相关信息，参数为搜索问题"

    def run(self, query: str) -> ToolResult:
        try:
            # 使用现有的向量检索
            docs = vector_manager.search(query, k=3)

            if not docs:
                return ToolResult(success=True, data="知识库中未找到相关信息")

            # 格式化结果
            results = []
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get("source", "未知")
                content = doc.page_content[:200]
                results.append(f"[{source}] {content}...")

            return ToolResult(success=True, data="\n\n".join(results))

        except Exception as e:
            return ToolResult(success=False, data=None, error=f"知识库查询失败: {e}")