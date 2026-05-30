---
name: news-fetcher
description: 获取最新新闻 — 支持国内、国际、科技分类，自动整理标题+摘要
trigger: "查新闻 / 新闻 / 国内新闻 / 国际新闻 / 科技新闻"
expected_requests:
  - "查一下今天的国内新闻"
  - "最新的国际新闻"
  - "科技圈有什么新闻"
  - "新闻速递"
---

# News Fetcher（新闻获取）

使用新浪新闻源（国内可访问），支持分类查询。

## 新闻源

| 分类 | URL |
|------|-----|
| 国内 | `https://news.sina.com.cn/china/` |
| 国际 | `https://news.sina.com.cn/world/` |
| 科技 | `https://tech.sina.com.cn/` |
| 综合 | `https://news.sina.com.cn/` |

## 查询方式

### 方式一：浏览器导航（推荐，JS 渲染完整）

使用 `browser_navigate` 打开对应 URL，然后 `browser_snapshot` 提取新闻标题。

### 方式二：curl + Python 解析（更快，但可能漏掉动态加载内容）

```bash
all_proxy=socks5://192.168.100.159:7897 curl -sL "https://news.sina.com.cn/china/" | python3 -c "
import sys, re
html = sys.stdin.read()
items = re.findall(r'<a[^>]*href=\"(https://news\\.sina\\.com\\.cn/[^\"]+)\"[^>]*>(.*?)</a>', html)
seen = set()
count = 0
for url, title in items:
    title = re.sub(r'<[^>]+>', '', title).strip()
    if title and len(title) > 10 and title not in seen:
        seen.add(title)
        count += 1
        print(f'{count}. {title}')
        if count >= 8:
            break
"
```

## 输出格式

每条新闻一行，带序号、标题、来源链接：

```
📰 【国内新闻】2026年5月30日
─────────────────────────
1. 标题内容……（来源：新浪）
2. 标题内容……（来源：新浪）
...
─────────────────────────
采集时间：2026-05-30 21:00
```

## 注意事项

1. 用户在中国大陆，部分外网可能无法直接访问。先直连，不通再走代理：
2. 新浪新闻源优先，容错备选：腾讯新闻、网易新闻、新华网
3. 新闻页面可能含动态加载内容，浏览器方式比 curl 更可靠
4. 标题长度控制在 30 字以内，过长则截断加"…"
