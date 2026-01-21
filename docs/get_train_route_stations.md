# get_train_route_stations 工具文档

## 功能说明
查询指定列车的经停站信息。输入车次号、出发站、到达站、日期，返回该车次所有经停站、到发时刻、停留时间等详细信息。

## 使用方法
### 请求参数
```json
{
  "from_station": "九江",
  "to_station": "永修",
  "train_date": "2025-06-01",
  "train_no": "G1234"
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
        "text": "{\"success\":true,\"train_no\":\"G1234\",\"train_date\":\"2025-06-01\",\"count\":5,\"stations\":[...]}"
      }
    ]
  }
}
```

### 解析后的JSON数据
```json
{
  "success": true,
  "train_no": "G1234",
  "train_date": "2025-06-01",
  "count": 5,
  "stations": [
    {
      "station_no": "1",
      "station_name": "九江",
      "arrive_time": "----",
      "start_time": "08:00",
      "stopover_time": "----"
    },
    {
      "station_no": "2",
      "station_name": "德安",
      "arrive_time": "08:10",
      "start_time": "08:12",
      "stopover_time": "2分"
    },
    {
      "station_no": "3",
      "station_name": "共青城",
      "arrive_time": "08:18",
      "start_time": "08:20",
      "stopover_time": "2分"
    },
    {
      "station_no": "4",
      "station_name": "庐山",
      "arrive_time": "08:22",
      "start_time": "08:24",
      "stopover_time": "2分"
    },
    {
      "station_no": "5",
      "station_name": "永修",
      "arrive_time": "08:26",
      "start_time": "----",
      "stopover_time": "----"
    }
  ]
}
```

### 返回字段说明
- `success`: 布尔值，表示查询是否成功
- `train_no`: 车次号
- `train_date`: 出发日期
- `count`: 经停站数量
- `stations`: 经停站列表
  - `station_no`: 站序
  - `station_name`: 车站名称
  - `arrive_time`: 到达时间
  - `start_time`: 出发时间
  - `stopover_time`: 停留时间
