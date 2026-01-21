"""日期工具"""

from datetime import datetime
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