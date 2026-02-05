"""
时间工具（增强版）
提供完整时间信息：年月日、星期、闰年等
"""
import datetime
import calendar
from app.tools.base import BaseTool, ToolResult


class TimeTool(BaseTool):
    """获取当前时间及详细时间信息"""

    name = "get_current_time"
    description = "获取当前完整时间信息，包括日期、星期、是否闰年等，无需参数"

    def run(self) -> ToolResult:
        now = datetime.datetime.now()

        year = now.year
        month = now.month
        day = now.day

        # ===== 星期 =====
        weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday = weekday_map[now.weekday()]

        # ===== 是否闰年 =====
        is_leap = calendar.isleap(year)

        # ===== 当年第几天 =====
        day_of_year = now.timetuple().tm_yday

        # ===== 本周第几天 =====
        day_of_week = now.isoweekday()  # 1-7

        # ===== 本月多少天 =====
        days_in_month = calendar.monthrange(year, month)[1]

        # ===== 是否月末 =====
        is_month_end = day == days_in_month

        # ===== 当前季度 =====
        quarter = (month - 1) // 3 + 1

        # ===== 是否周末 =====
        is_weekend = day_of_week in [6, 7]

        # ===== 结构化结果 =====
        result = {
            "formatted_time": now.strftime("%Y年%m月%d日 %H:%M:%S"),
            "year": year,
            "month": month,
            "day": day,
            "weekday": weekday,
            "quarter": quarter,
            "is_leap_year": is_leap,
            "day_of_year": day_of_year,
            "day_of_week": day_of_week,
            "days_in_month": days_in_month,
            "is_month_end": is_month_end,
            "is_weekend": is_weekend,
            "timestamp": int(now.timestamp())
        }

        return ToolResult(success=True, data=result)
