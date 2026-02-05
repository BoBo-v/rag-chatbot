"""
计算器工具
"""
from app.tools.base import BaseTool, ToolResult


class CalculatorTool(BaseTool):
    """数学计算"""

    name = "calculate"
    description = "计算数学表达式，参数为表达式字符串，如 '123*456'"

    def run(self, expression: str) -> ToolResult:
        try:
            # 安全的数学计算（只允许数字和运算符）
            allowed = set("0123456789+-*/.() ")
            if not all(c in allowed for c in expression):
                return ToolResult(success=False, data=None, error="表达式包含非法字符")

            result = eval(expression)
            return ToolResult(success=True, data=str(result))
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"计算错误: {e}")