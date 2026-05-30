---
name: weather-forecast
description: 查询任意城市的天气预报（气温、天气状况、湿度、风速等）
trigger: "查天气 / 天气预报 / 气温 / weather"
expected_requests:
  - "明天珠海天气怎么样"
  - "查一下北京今天的温度"
  - "上海下周天气"
  - "深圳今天会下雨吗"
---

# Weather Forecast (天气预报)

使用 wttr.in API 查询天气数据，支持中文城市名。

## 查询命令

```bash
curl -s "wttr.in/{城市名}?format=j1"
```

返回 JSON，关键字段：

| 字段 | 含义 |
|------|------|
| `current_condition[0].temp_C` | 当前温度(°C) |
| `current_condition[0].humidity` | 湿度(%) |
| `current_condition[0].windspeedKmph` | 风速(km/h) |
| `current_condition[0].weatherDesc[0].value` | 天气描述 |
| `weather[N].date` | 日期 (YYYY-MM-DD) |
| `weather[N].maxtempC` | 最高温 |
| `weather[N].mintempC` | 最低温 |
| `weather[N].hourly[0].weatherDesc[0].value` | 当日天气描述 |
| `nearest_area[0].areaName[0].value` | 匹配到的城市名 |

`weather` 数组索引: [0]=今天, [1]=明天, [2]=后天

## 输出格式

简洁中文输出，结论先行：

```
**{城市} {日期} 天气预报**
🌡️ **当前温度：**{temp}°C
🌡️ **最高温：**{max}°C / **最低温：**{min}°C
🌤️ **天气：**{desc}
💧 **湿度：**{humidity}%
💨 **风速：**{windspeed} km/h
```

- 若只有当天数据，只显示当天
- 若用户问"明天" "后天" 等，定位到对应索引
- 温差小（≤4°C）提醒"体感较闷"
- 预报有雨时提醒**带伞**
- 气温超过 35°C 提醒**注意防暑**

## 注意事项

1. wttr.in 需要外网访问，**必须走 SOCKS5 代理**（用户位于中国）
2. 代理设置：`all_proxy=socks5://192.168.100.159:7897`
3. 使用 `format=j1` 获取完整 JSON，避免解析 HTML
4. 城市名支持中文（如"珠海""上海""北京"）
5. 免费服务，无需 API Key
