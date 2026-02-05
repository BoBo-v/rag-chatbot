"""
网络搜索工具
"""
from app.tools.base import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    """网络搜索"""

    name = "web_search"
    description = "搜索互联网获取最新信息，参数为搜索关键词"

    def run(self, query: str) -> ToolResult:
        if not query:
            return ToolResult(success=False, data=None, error="请提供搜索关键词")
        try:
            # 使用 DuckDuckGo（免费，无需 API Key）
            try:
                from ddgs import DDGS
            except ImportError:
                # 兼容旧版
                from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))

            if not results:
                return ToolResult(success=True, data="未找到相关信息")

            # 格式化结果
            snippets = []
            for r in results:
                snippets.append(f"• {r['title']}\n  {r['body'][:150]}...")

            return ToolResult(success=True, data="\n\n".join(snippets))

        except ImportError:
            return ToolResult(
                success=False,
                data=None,
                error="请安装 duckduckgo-search: pip install duckduckgo-search"
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"搜索失败: {e}")