# query_tickets 工具文档

## 功能说明
官方 12306 余票/车次/座席/时刻一站式查询。输入出发站、到达站、日期，返回所有可购车次、时刻、历时、各席别余票等详细信息。支持中文名、三字码。

## 使用方法
### 请求参数
```json
{
  "from_station": "九江",
  "to_station": "永修",
  "train_date": "2025-06-01"
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
        "text": "{\"success\":true,\"from_station\":\"九江\",\"to_station\":\"永修\",\"train_date\":\"2025-06-01\",\"count\":2,\"trains\":[...]}"
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
  "count": 2,
  "trains": [
    {
      "train_no": "G1234",
      "from_station": "九江",
      "from_station_code": "JJG",
      "to_station": "永修",
      "to_station_code": "ACG",
      "start_time": "08:00",
      "arrive_time": "08:26",
      "duration": "00:26",
      "seats": {
        "business": "有",
        "first_class": "有",
        "second_class": "20"
      }
    },
    {
      "train_no": "D5678",
      "from_station": "九江",
      "from_station_code": "JJG",
      "to_station": "永修",
      "to_station_code": "ACG",
      "start_time": "10:30",
      "arrive_time": "11:00",
      "duration": "00:30",
      "seats": {
        "first_class": "5",
        "second_class": "15"
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
- `trains`: 车次列表数组
  - `train_no`: 车次号
  - `from_station`: 出发站全称
  - `from_station_code`: 出发站三字码
  - `to_station`: 到达站全称
  - `to_station_code`: 到达站三字码
  - `start_time`: 出发时间
  - `arrive_time`: 到达时间
  - `duration`: 历时
  - `seats`: 座位信息对象，包含各种座型余票
    - `business`: 商务座
    - `first_class`: 一等座
    - `second_class`: 二等座
    - `soft_sleeper`: 软卧
    - `hard_sleeper`: 硬卧
    - `hard_seat`: 硬座
    - `no_seat`: 无座
