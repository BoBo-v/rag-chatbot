"""
工具基类 - 所有工具继承这个类
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None


class BaseTool(ABC):
    """工具基类"""

    name: str = "base_tool"
    description: str = "基础工具"

    @abstractmethod
    def run(self, *args, **kwargs) -> ToolResult:
        """执行工具（子类必须实现）"""
        pass

    def __call__(self, *args, **kwargs) -> ToolResult:
        """让工具可以像函数一样调用"""
        try:
            return self.run(*args, **kwargs)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))