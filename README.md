# 热点新闻收集与推送工具 (Hot News Daily Push)

这是一个自动收集各大平台热点新闻、RSS订阅源以及特定Twitter Feed，进行处理、去重、总结，并通过多种渠道推送热点摘要的工具。

## 功能特点

- **多源数据收集**：
    - 支持从30+个平台（如微博、知乎、百度、抖音等）收集热点数据
    - **支持通过配置文件 `config/config.py` 中的 `RSS_FEEDS` 列表订阅多个RSS源**
    - **集成特定Twitter Feed** (通过GitHub Raw获取指定账号的推文)
- **智能内容处理**：
    - 使用 `cloudscraper` 尝试绕过部分网站的Cloudflare保护获取RSS内容
    - **标题去重**：在处理前基于完全相同的标题进行去重，优先保留来自RSS和Twitter的内容
    - 抓取网页原文以补充摘要（按需）
    - **智能摘要生成/处理**：
        - 优先使用RSS源提供的有效摘要（过长会截断）
        - 如无有效摘要，使用腾讯混元大模型生成摘要
        - 如AI生成失败，使用原文内容截断作为备选摘要
- **AI驱动的最终总结**：
    - 使用DeepSeek AI模型对去重和处理后的信息列表进行最终归纳总结
    - **优化Prompt**：指导Deepseek理解包含社交媒体信息，并合并内容相似的条目
- **多渠道推送**：支持9种不同的推送渠道，包括企业微信、钉钉、飞书、Telegram等
- **定制化配置**：可通过环境变量灵活配置信息源、推送渠道和AI模型参数
- **科技热点筛选**：可选择只收集和推送科技相关热点 (目前主要影响热榜和Deepseek总结)
- **缓存机制**：支持摘要缓存，提高运行效率
- **自动清理**：自动清理旧的数据和日志文件

## 项目结构

```
├── cache/              # 缓存目录，存储摘要缓存等
├── config/             # 配置文件目录
│   ├── config.py       # 主要配置文件 (包含 SOURCE_NAME_MAP, RSS_FEEDS 等)
│   └── __init__.py
├── crawler/            # 数据爬取模块
│   ├── data_collector.py  # 热点、RSS、Twitter数据收集
│   ├── rss_parser.py      # RSS条目解析辅助函数
│   └── web_crawler.py     # 网页内容爬取 (包括提取时间戳)
│   └── __init__.py
├── data/               # 数据存储目录 (默认被.gitignore忽略)
│   ├── filtered/       # 过滤后的热点数据
│   ├── inputs/         # LLM 输入数据
│   ├── merged/         # 合并处理后的数据
│   ├── outputs/        # LLM 输出数据
│   ├── raw/            # 原始热点数据
│   └── webhook/        # 推送内容和响应数据
├── llm_integration/    # 大语言模型集成模块
│   ├── deepseek_integration.py  # DeepSeek模型集成 (最终总结)
│   └── hunyuan_integration.py   # 腾讯混元模型集成 (单条摘要)
│   └── __init__.py
├── notification/       # 通知推送模块
│   ├── notify.py       # 通用通知函数 (已废弃，待移除)
│   └── webhook_sender.py  # Webhook推送实现 (包括多种渠道)
│   └── __init__.py
├── processor/          # 数据处理模块
│   └── news_processor.py  # 新闻/信息处理 (摘要生成/截断、时间戳提取)
│   └── __init__.py
├── tests/              # 测试代码目录
│   └── test_web_crawler.py # 网页抓取功能测试
│   └── __init__.py
├── utils/              # 工具函数模块
│   └── utils.py        # 通用工具函数
│   └── __init__.py
├── .env                # 环境变量配置文件（需自行创建）
├── .env.example        # 环境变量示例文件
├── .gitignore          # Git忽略文件配置
├── hot_news_main.py    # 主程序入口
├── requirements.txt    # Python依赖项列表
└── README.md           # 项目说明文档
```

## 安装与配置

### 1. 克隆仓库

```bash
git clone <repository-url>
cd hot_news_daily_push
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例环境变量文件并进行配置：

```bash
cp .env.example .env
```

编辑`.env`文件，配置以下**必要**参数：

```dotenv
# --- API密钥 ---
DEEPSEEK_API_KEY="your_deepseek_api_key"  # DeepSeek AI API密钥 (用于最终总结)
HUNYUAN_API_KEY="your_hunyuan_api_key"    # 腾讯混元大模型API密钥 (用于生成单条摘要，如果SKIP_CONTENT=false则必需)

# --- 推送渠道 (至少配置一种) ---
# 以企业微信机器人为例
QYWX_KEY="your_qywx_key"
# 或其他渠道，如钉钉、飞书、Telegram等，参考 .env.example
# WEBHOOK_URL="your_webhook_url" # 通用Webhook也可作为一种简单方式
```

### 4. (可选) 配置RSS源

编辑 `config/config.py` 文件中的 `RSS_FEEDS` 列表，添加你想订阅的RSS源。格式如下：

```python
RSS_FEEDS = [
    {"name": "科技博客A", "url": "https://example.com/tech/rss.xml"},
    {"name": "公众号-XXX", "url": "https://example.com/weixin/rss.xml"},
    # ... 更多RSS源
]
```
如果 `RSS_FEEDS` 列表为空，程序会尝试使用 `.env` 文件中的 `RSS_URL` 作为单个RSS源（如果已配置）。

### 5. (可选) 配置其他环境变量

根据需要编辑 `.env` 文件，调整其他参数，如 `TECH_ONLY`, `MAX_WORKERS` 等。详细说明见下文。

## 使用方法

### 运行主程序

```bash
python hot_news_main.py
```
程序将执行以下主要步骤：
1.  **收集数据**: 获取热榜、RSS源、Twitter Feed的内容。
2.  **初步过滤**: 筛选掉过旧的内容。
3.  **去重**: 基于完全相同的标题进行去重，优先保留RSS和Twitter来源。
4.  **内容处理**: (如果 `SKIP_CONTENT=False`)
    *   检查每个条目是否已有有效摘要。
    *   如果摘要无效或缺失，尝试抓取原文。
    *   如果原文存在，尝试调用腾讯混元生成摘要。
    *   如果AI失败，截断原文作为摘要。
    *   如果原文抓取失败，标记为无摘要。
    *   过长的有效摘要会被截断。
5.  **最终总结**: 将处理后的信息列表发送给Deepseek进行归纳总结。
6.  **推送结果**: 将Deepseek生成的总结通过配置的渠道推送。
7.  **清理**: 删除旧的数据文件。

### 命令行参数

(注意: 环境变量优先于命令行参数)

```bash
# 只处理和总结科技相关内容
export TECH_ONLY=True
python hot_news_main.py

# 禁用摘要缓存 (强制重新生成)
export NO_CACHE=True
python hot_news_main.py

# 跳过内容处理步骤 (步骤4)，直接使用原始内容进行总结
export SKIP_CONTENT=True
python hot_news_main.py
```

## 环境变量说明

### 基础配置

| 变量名 | 说明 | 默认值 (来自config.py) |
|-------|------|-------|
| `TECH_ONLY` | 是否只处理科技热点 (影响热榜源选择和Deepseek总结Prompt) | `False` |
| `NO_CACHE` | 是否禁用腾讯混元摘要缓存 | `False` |
| `SKIP_CONTENT` | 是否跳过内容处理步骤(抓取原文、生成/截断摘要) | `False` |
| `BASE_URL` | 热点数据API基础URL (hotApi项目) | `https://api-hot.imsyy.top` |
| `MAX_WORKERS` | 处理内容时的最大并发数 (腾讯混元API调用并发) | `5` |
| `FILTER_DAYS` | 过滤多少天内的热榜/RSS/推文 | `1` |
| `RSS_DAYS` | 获取RSS中最近几天的文章 (如果 `FILTER_DAYS` 未设置，则使用此值) | `1` |
| `HOTSPOT_LIMIT` | 每个热榜来源获取的热点数量限制 | `1` |

### RSS配置

| 变量名 | 说明 | 默认值 (来自config.py) |
|-------|------|-------|
| `RSS_URL` | 单个RSS源URL (**仅在 `config.py` 中 `RSS_FEEDS` 列表为空时生效**) | `None` |
| `RSS_FEEDS` | 在 `config/config.py` 中配置，包含名称和URL的字典列表 | `[]` (空列表) |

##***REMOVED***

| 变量名 | 说明 | 是否必需 |
|-------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek AI API密钥 | **是** |
| `HUNYUAN_API_KEY` | 腾讯混元大模型API密钥 | **是** (除非`SKIP_CONTENT=True`) |
| `DEEPSEEK_API_URL` | DeepSeek API接口地址 (可选，覆盖默认) | 否 |
| `DEEPSEEK_MODEL_ID` | DeepSeek模型ID (可选，覆盖默认) | 否 |

### 推送渠道配置

(请参考 `.env.example` 获取所有支持的渠道和变量名)

| 变量名 (部分示例) | 说明 | 配置示例 |
|-------|------|--------|
| `QYWX_KEY` | 企业微信机器人key | `693axxx-xxxx-xxxx-xxxx-xxxxx` |
| `DD_BOT_TOKEN` & `DD_BOT_SECRET` | 钉钉机器人Token和Secret | `xxxxxxxx` & `SECxxxxxxxx` |
| `FSKEY` | 飞书机器人Key | `xxxxxxxxxxxxxxxx` |
| `TG_BOT_TOKEN` & `TG_USER_ID` | Telegram机器人Token和用户ID | `123:...` & `123456` |
| ... | 其他渠道 | ... |

## 常见问题

### 1. 为什么有些摘要是空的或类似 "[摘要无法生成：无内容]"?

可能的原因：
    *   **原文抓取失败**：目标网站限制访问、结构复杂或已失效。
    *   **内容不足**：抓取到的原文太短，无法生成有意义的摘要。
    *   **腾讯混元API调用失败**：API密钥错误、网络问题或API服务异常。
    *   **原始RSS摘要无效且无内容**：RSS源本身只提供标题或无效摘要，且无法抓取原文。

### 2. 为什么有些摘要被截断了 (以 "..." 结尾)?

*   **原始RSS摘要过长**：`processor/news_processor.py` 中 `FINAL_DESC_MAX_LENGTH` (默认300) 限制了直接使用的摘要长度，超过会截断。
*   **AI生成失败后的备选摘要**：如果腾讯混元生成失败，程序会尝试截断抓取到的原文 (`FALLBACK_DESC_LENGTH` 默认500字符) 作为备选摘要。

### 3. Twitter Feed 数据是如何获取和处理的?

*   数据源于 `https://raw.githubusercontent.com/tuber0613/x-kit/main/tweets/` 下按日期组织的JSON文件。
*   `crawler/data_collector.py` 中的 `fetch_twitter_feed` 函数负责获取这些文件。
*   推文的完整内容会作为初始 `desc` 字段，标题是截断后的推文内容。
*   如果推文内容（作为`desc`）超过300字符，在处理阶段会被截断。**目前不会为推文调用混元生成摘要**。
*   在去重阶段，Twitter来源的内容享有较高优先级。
*   Deepseek已被告知要考虑Twitter来源的信息。

### 4. 去重逻辑是如何工作的？

*   在调用Deepseek总结之前，`hot_news_main.py` 会进行一轮去重。
*   它基于**完全相同**的 `title` 字段进行判断。
*   如果标题相同，会优先保留 `source` 为 "RSS" 或 "Twitter" 的条目。如果来源优先级相同，则保留先遇到的条目。
*   Deepseek的Prompt也要求它进一步合并**内容相似但标题可能不同**的条目。

### 5. 如何添加或修改支持的热榜来源?

*   主要的热榜来源由 `BASE_URL` 指向的API (`https://api-hot.imsyy.top`) 提供。你需要查看该API的文档了解支持的来源标识符。
*   在 `config/config.py` 中的 `ALL_SOURCES` 或 `TECH_SOURCES` 列表中添加或移除这些标识符。

### 6. 如何解决 Cloudflare 保护导致的 RSS 获取失败?

*   程序已使用 `cloudscraper` 库尝试模拟浏览器行为绕过简单的 Cloudflare 检查。
*   对于需要复杂验证（如JS挑战、验证码）的站点，`cloudscraper` 可能仍然失败。日志中会记录相关警告。
*   目前没有完美的解决方案，可以尝试寻找该站点的其他RSS源或联系站点管理员。

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。