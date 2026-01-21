import os
import re
import aiofiles
import logging
from typing import Optional

class Station:
    def __init__(self, name, code, pinyin, py_short, num, city=None):
        self.name = name
        self.code = code
        self.pinyin = pinyin
        self.py_short = py_short
        self.num = num
        self.city = city  # 城市字段可选

    def __repr__(self):
        return f"Station(name={self.name}, code={self.code}, pinyin={self.pinyin}, city={self.city})"

class StationSearchResult:
    def __init__(self, stations):
        self.stations = stations

class StationService:
    def __init__(self):
        self.stations = []

    async def load_stations(self, path=None):
        """
        解析12306原始JS，提取站点及所属城市信息
        自动检测并修复字段顺序异常的数据行，增强排列组合尝试。
        """
        # 计算默认绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        default_path = os.path.normpath(os.path.join(current_dir, "..", "resources", "station_name.js"))
        
        target_path = path
        if target_path is None:
            target_path = default_path
            
        if not os.path.exists(target_path):
            logging.warning(f"指定路径不存在: {target_path}")
            # 如果指定路径不存在，且不是默认路径，尝试使用默认路径
            if target_path != default_path and os.path.exists(default_path):
                logging.info(f"尝试使用默认资源路径: {default_path}")
                target_path = default_path
            else:
                logging.error(f"无法找到站点文件，请检查安装完整性。路径: {target_path}")
                return

        async with aiofiles.open(target_path, mode="r", encoding="utf-8") as f:
            content = await f.read()
        m = re.search(r"var station_names ?= ?'(.*?)';", content)
        if not m:
            m = re.search(r"'(@[^']+)';", content)
        if not m:
            logging.error("未能解析到站点JS内容")
            return
        data = m.group(1)
        stations_raw = [s for s in data.split('@') if s]
        result = []
        for st in stations_raw:
            parts = st.split('|')
            if len(parts) < 8:
                logging.warning(f"字段数异常，跳过：{st}")
                continue
            # 正确解析顺序：@id|车站名|三字码|拼音|简拼|编号|区域码|城市|...
            name = parts[1].strip()
            code = parts[2].strip()
            pinyin = parts[3].strip()
            py_short = parts[4].strip()
            num = parts[5].strip()
            city = parts[7].strip()
            # 检查三字码、拼音、简拼是否合规，否则尝试排列组合
            def is_code(val):
                return val.isalpha() and val.isupper() and len(val) == 3
            def is_pinyin(val):
                return val.isalpha() and val.islower() and len(val) >= 2
            def is_py_short(val):
                return val.isalpha() and val.islower() and 1 <= len(val) <= 8
            if not is_code(code):
                found = False
                for idx in range(1, min(5, len(parts))):
                    if is_code(parts[idx]):
                        code = parts[idx]
                        found = True
                        logging.warning(f"自动排列修正三字码：{name} => {code}")
                        break
                if not found:
                    logging.warning(f"三字码无法修正：{st}")
            if not is_pinyin(pinyin):
                found = False
                for idx in range(1, min(6, len(parts))):
                    if is_pinyin(parts[idx]):
                        pinyin = parts[idx]
                        found = True
                        logging.warning(f"自动排列修正拼音：{name} => {pinyin}")
                        break
                if not found:
                    logging.warning(f"拼音无法修正：{st}")
            if not is_py_short(py_short):
                found = False
                for idx in range(1, min(7, len(parts))):
                    if is_py_short(parts[idx]):
                        py_short = parts[idx]
                        found = True
                        logging.warning(f"自动排列修正简拼：{name} => {py_short}")
                        break
                if not found:
                    logging.warning(f"简拼无法修正：{st}")
            result.append(Station(name, code, pinyin, py_short, num, city))
        self.stations = result
        logging.info(f"已加载{len(self.stations)}个车站（含城市信息，自动排列修正字段）")

    async def get_station_by_name(self, name):
        name = name.strip()
        if name.endswith("站") and len(name) > 2:
            name = name[:-1]
        for s in self.stations:
            if s.name.strip() == name:
                return s
        return None

    async def get_station_by_code(self, code):
        for s in self.stations:
            if s.code == code:
                return s
        return None

    async def search_stations(self, query, limit=10):
        query = query.strip().lower()
        if query.endswith("站") and len(query) > 2:
            query = query[:-1]
        results = []
        matched_ids = set()
        # 1. 精确匹配
        for s in self.stations:
            if (query == s.name.strip().lower() or
                query == s.code.lower() or
                query == s.pinyin.lower() or
                query == s.py_short.lower()):
                results.append(s)
                matched_ids.add(id(s))
                if len(results) >= limit:
                    return StationSearchResult(results)
        # 2. 模糊匹配（含city）
        for s in self.stations:
            if id(s) in matched_ids:
                continue
            if (query in s.name.strip().lower() or
                query in s.pinyin.lower() or
                query in s.py_short.lower() or
                query in s.code.lower() or
                (s.city and query in s.city.lower())):
                results.append(s)
                if len(results) >= limit:
                    break
        return StationSearchResult(results)

    async def get_station_code(self, query: str) -> Optional[str]:
        if not query:
            return None
        q = query.strip()
        # 兼容“站”
        if q.endswith("站") and len(q) > 2:
            q = q[:-1]
        # 1. 精确匹配 name（区分大小写，通常为中文）
        for s in self.stations:
            if q == s.name:
                return s.code
        # 2. 精确匹配 code（三字码，区分大小写，通常为大写）
        for s in self.stations:
            if q == s.code:
                return s.code
        return None