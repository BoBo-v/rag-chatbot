"""
天气工具 - 使用网络搜索获取真实天气
"""
from app.tools.base import BaseTool, ToolResult


class WeatherTool(BaseTool):
    """获取天气信息"""

    name = "get_weather"
    description = "获取指定城市的天气，参数为城市名称，如 '北京'"

    def run(self, city: str = "北京") -> ToolResult:
        try:
            from duckduckgo_search import DDGS

            # 搜索天气
            query = f"{city}今天天气"

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))

            if not results:
                return ToolResult(success=True, data=f"{city}天气信息未找到")

            # 提取天气信息
            weather_info = []
            for r in results:
                weather_info.append(f"{r['title']}: {r['body'][:100]}")

            return ToolResult(success=True, data="\n".join(weather_info[:2]))

        except ImportError:
            # 如果没装搜索库，返回模拟数据
            return ToolResult(success=True, data=f"{city}天气：晴，温度 20°C（模拟数据）")

        except Exception as e:
            return ToolResult(success=False, data=None, error=f"获取天气失败: {e}")