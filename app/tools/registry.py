"""
工具注册表 - 管理所有可用工具
"""
from typing import Dict, List, Optional
from app.tools.base import BaseTool
from app.tools.time_tool import TimeTool
from app.tools.calculator import CalculatorTool
from app.tools.weather_tool import WeatherTool
from app.tools.search_tool import WebSearchTool
from app.tools.rag_tools import RAGTool


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool
        print(f"  ✓ 注册工具: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有工具名"""
        return list(self._tools.keys())

    def get_tools_description(self) -> str:
        """获取所有工具的描述（用于 Prompt）"""
        descriptions = []
        for name, tool in self._tools.items():
            descriptions.append(f"- {name}: {tool.description}")
        return "\n".join(descriptions)

    def execute(self, tool_name: str, *args, **kwargs):
        """执行工具"""
        tool = self.get(tool_name)
        if not tool:
            return None
        return tool(*args, **kwargs)


def create_default_registry() -> ToolRegistry:
    """创建默认的工具注册表"""
    registry = ToolRegistry()

    # 注册所有工具
    registry.register(TimeTool())
    registry.register(CalculatorTool())
    #registry.register(WeatherTool())
    registry.register(WebSearchTool())
    registry.register(RAGTool())

    return registry


# 全局工具注册表
tool_registry = create_default_registry()