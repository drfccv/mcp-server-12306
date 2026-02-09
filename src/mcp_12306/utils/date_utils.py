"""日期工具"""

from datetime import datetime, date, timedelta
import re


def validate_date(date_str: str) -> bool:
    """验证日期格式"""
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False
        
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_date_not_past(date_str: str) -> tuple[bool, str]:
    """
    验证日期格式并检查是否在有效范围内（今天到14天后）
    返回: (是否有效, 错误信息或空字符串)
    
    12306允许查询的日期范围是提前14天售票，因此：
    - 不能查询历史日期（当天前）
    - 不能查询超过14天后的日期
    """
    # 先验证格式
    if not validate_date(date_str):
        return False, "日期格式错误，请使用 YYYY-MM-DD 格式"
    
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        query_date = dt.date()
        today = date.today()
        max_date = today + timedelta(days=14)
        
        # 检查是否早于今天
        if query_date < today:
            return False, f"出发日期不能早于今天（{today.strftime('%Y-%m-%d')}），12306无法查询历史日期的车次信息"
        
        # 检查是否超过14天后
        if query_date > max_date:
            return False, f"出发日期不能晚于{max_date.strftime('%Y-%m-%d')}，12306仅支持提前14天购票"
        
        return True, ""
    except Exception as e:
        return False, f"日期校验失败: {str(e)}"