# search_stations 工具文档

## 功能说明
智能车站搜索。支持中文名、拼音、简拼、三字码（Code）。
可用于模糊搜索（如“北京”），也可用于精确获取车站代码（如输入“BJP”返回北京站信息）。

## 使用方法
### 请求参数
```json
{
  "query": "九江",
  "limit": 10
}
```

或者通过三字码精确搜索：
```json
{
  "query": "JJG",
  "limit": 1
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
        "text": "{\"success\":true,\"query\":\"九江\",\"count\":2,\"stations\":[{\"name\":\"九江\",\"code\":\"JJG\",\"pinyin\":\"jiujiang\",\"py_short\":\"jj\",\"num\":\"1234\"},{\"name\":\"九江西\",\"code\":\"JXG\",\"pinyin\":\"jiujiangxi\",\"py_short\":\"jjx\"}]}"
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
  "count": 2,
  "stations": [
    {
      "name": "九江",
      "code": "JJG",
      "pinyin": "jiujiang",
      "py_short": "jj",
      "num": "1234"
    },
    {
      "name": "九江西",
      "code": "JXG",
      "pinyin": "jiujiangxi",
      "py_short": "jjx"
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
  - `num`: 车站编号（可选）
