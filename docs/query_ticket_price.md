# query_ticket_price 工具文档

## 功能说明
查询火车票价信息。输入出发站、到达站、日期，返回各车次的票价详情。支持指定车次号过滤。

## 使用方法
### 请求参数
```json
{
  "from_station": "九江",
  "to_station": "永修",
  "train_date": "2025-06-01",
  "train_code": "G1556"  // 可选，指定车次号过滤
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
        "text": "{\"success\":true,\"from_station\":\"九江\",\"to_station\":\"永修\",\"train_date\":\"2025-06-01\",\"count\":1,\"data\":[...]}"
      }
    ]
  }
}
```

### 解析后的JSON数据
```json
{
  "success": true,
  "from_station": "九江",
  "to_station": "永修",
  "train_date": "2025-06-01",
  "count": 1,
  "data": [
    {
      "train_no": "5l000G155600",
      "train_code": "G1556",
      "from_station": "九江",
      "to_station": "永修",
      "start_time": "08:00",
      "arrive_time": "08:26",
      "duration": "00:26",
      "train_class_name": "高速",
      "prices": {
        "二等座": "23.0",
        "一等座": "37.0",
        "商务座": "70.5"
      }
    }
  ]
}
```

### 返回字段说明
- `success`: 布尔值，表示查询是否成功
- `from_station`: 出发站名称
- `to_station`: 到达站名称
- `train_date`: 出发日期
- `count`: 车次数量
- `data`: 车次列表数组
  - `train_no`: 内部车次号
  - `train_code`: 车次代码（如 G1556）
  - `from_station`: 出发站名称
  - `to_station`: 到达站名称
  - `start_time`: 出发时间
  - `arrive_time`: 到达时间
  - `duration`: 历时
  - `train_class_name`: 列车类型（如高速、动车）
  - `prices`: 票价信息对象（单位：元）
    - `商务座`: 商务座票价
    - `一等座`: 一等座票价
    - `二等座`: 二等座票价
    - `软卧`: 软卧票价
    - `硬卧`: 硬卧票价
    - `硬座`: 硬座票价
    - `无座`: 无座票价
    - ... 其他席别
