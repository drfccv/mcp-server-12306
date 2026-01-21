# query_transfer 工具文档

## 功能说明
官方 12306 一次中转换乘方案查询。输入出发站、到达站、日期，返回一次换乘的最优方案，含所有中转车次、时刻、余票、历时等详细信息。

## 使用方法
### 请求参数
```json
{
  "from_station": "九江",
  "to_station": "永修",
  "train_date": "2025-06-01",
  "middle_station": "",
  "isShowWZ": "N",
  "purpose_codes": "00"
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
        "text": "{\"success\":true,\"from_station\":\"九江\",\"to_station\":\"永修\",\"train_date\":\"2025-06-01\",\"count\":2,\"transfers\":[...]}"
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
  "transfers": [
    {
      "middle_station": "南昌",
      "total_duration": "02:10",
      "wait_time": "00:30",
      "segments": [
        {
          "train_no": "G1234",
          "from_station": "九江",
          "to_station": "南昌",
          "start_time": "08:00",
          "arrive_time": "08:30",
          "duration": "00:30",
          "seats": {
            "second_class": "有",
            "no_seat": "有"
          }
        },
        {
          "train_no": "G5678",
          "from_station": "南昌",
          "to_station": "永修",
          "start_time": "09:00",
          "arrive_time": "09:40",
          "duration": "00:40",
          "seats": {
            "second_class": "15",
            "no_seat": "有"
          }
        }
      ]
    }
  ]
}
```

### 返回字段说明
- `success`: 布尔值，表示查询是否成功
- `from_station`: 出发站名称
- `to_station`: 到达站名称
- `train_date`: 出发日期
- `count`: 中转方案数量
- `transfers`: 中转方案列表
  - `middle_station`: 中转站
  - `total_duration`: 总历时
  - `wait_time`: 等候时间
  - `segments`: 车次段列表（两段）
    - `train_no`: 车次号
    - `from_station`: 出发站
    - `to_station`: 到达站
    - `start_time`: 出发时间
    - `arrive_time`: 到达时间
    - `duration`: 历时
    - `seats`: 座位余票信息
