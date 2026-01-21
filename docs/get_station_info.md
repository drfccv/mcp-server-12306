# get_station_info 工具文档

## 功能说明
获取指定车站的详细信息。输入车站名称或三字码，返回该站的中文名、三字码、拼音等详细资料。

**注意**: 此工具实际上调用的是 `search_stations` 功能，用于车站信息查询。

## 使用方法
### 请求参数
```json
{
  "query": "九江",
  "limit": 10
}
```

### 返回示例（JSON格式）
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\":true,\"query\":\"九江\",\"count\":7,\"stations\":[...]}"
      }
    ]
  }
}
```

### 解析后的JSON数据
```json
{
  "success": true,
  "query": "九江",
  "count": 7,
  "stations": [
    {
      "name": "九江",
      "code": "JJG",
      "pinyin": "jiujiang",
      "py_short": "jj",
      "num": "677"
    },
    {
      "name": "共青城",
      "code": "GAG",
      "pinyin": "gongqingcheng",
      "py_short": "gqc",
      "num": "510"
    },
    {
      "name": "庐山",
      "code": "LSG",
      "pinyin": "lushan",
      "py_short": "ls",
      "num": "846"
    },
    {
      "name": "彭泽",
      "code": "PZG",
      "pinyin": "pengze",
      "py_short": "pz",
      "num": "1033"
    },
    {
      "name": "德安",
      "code": "DAG",
      "pinyin": "dean",
      "py_short": "da",
      "num": "1817"
    },
    {
      "name": "都昌",
      "code": "DCG",
      "pinyin": "duchang",
      "py_short": "dc",
      "num": "1829"
    },
    {
      "name": "湖口",
      "code": "HKG",
      "pinyin": "hukou",
      "py_short": "hk",
      "num": "2116"
    }
  ]
}
```

### 返回字段说明
- `success`: 布尔值，表示查询是否成功
- `query`: 搜索关键词
- `count`: 找到的车站数量
- `stations`: 车站列表数组
  - `name`: 车站全称
  - `code`: 车站三字码
  - `pinyin`: 全拼
  - `py_short`: 简拼
  - `num`: 车站编号

      **8.** 🚉 **瑞昌** `(RCG)`
       📍 拼音: `ruichang` | 简拼: `rc`
       🔢 编号: `2681`

      **9.** 🚉 **瑞昌西** `(RXG)`
       📍 拼音: `ruichangxi` | 简拼: `rcx`
       🔢 编号: `2682`

      **10.** 🚉 **永修** `(ACG)`
       📍 拼音: `yongxiu` | 简拼: `yx`
       🔢 编号: `3245`
      "

    }
  ]
}
```
