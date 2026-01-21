# get_current_time 工具文档

## 功能说明
获取当前时间，支持时区参数。

## 使用方法
### 请求参数
```json
{
  "timezone": "Asia/Shanghai",
  "format": "YYYY-MM-DD"
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
        "text": "{\"success\":true,\"timezone\":\"Asia/Shanghai\",\"datetime\":\"2025-06-01 14:30:00\",\"date\":\"2025-06-01\",\"time\":\"14:30:00\",\"timestamp\":1748760600}"
      }
    ]
  }
}
```

### 解析后的JSON数据
```json
{
  "success": true,
  "timezone": "Asia/Shanghai",
  "datetime": "2025-06-01 14:30:00",
  "date": "2025-06-01",
  "time": "14:30:00",
  "timestamp": 1748760600
}
```

### 返回字段说明
- `success`: 布尔值，表示查询是否成功
- `timezone`: 时区
- `datetime`: 完整日期时间
- `date`: 日期
- `time`: 时间
- `timestamp`: Unix时间戳
