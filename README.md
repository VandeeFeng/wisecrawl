# 热点新闻收集与推送工具 (Hot News Daily Push)

这是一个自动收集各大平台热点新闻、RSS订阅源以及特定Twitter Feed，进行处理、去重、总结，并通过多种渠道推送热点摘要的工具。

该项目完全由Cursor和Trae接力编写，鄙人只动脑子和嘴，如有问题还请海涵~

## 功能特点

- **多源数据收集**：
    - 支持从30+个平台（如微博、知乎、百度、抖音等）收集热点数据 (依赖外部API: `https://api-hot.imsyy.top`，基于项目 [DailyHotApi](https://github.com/imsyy/DailyHotApi))
    - **支持通过配置文件 `config/config.py` 中的 `RSS_FEEDS` 列表订阅多个RSS源**
      - 微信公众号文章通过 [wewe-rss](https://github.com/cooderl/wewe-rss) 项目转换为RSS源
    - **集成特定Twitter Feed** (通过 [x-kit](https://github.com/tuber0613/x-kit) 项目获取指定账号的推文 - 默认获取近2天，处理时筛选近24小时)
- **智能内容处理**：
    - 使用 `cloudscraper` 尝试绕过部分网站的Cloudflare保护获取RSS内容
    - **尝试从RSS Feed中预提取内容** (如 `content:encoded`)，减少后续网页抓取需求
    - **标题去重**：在处理后、总结前基于完全相同的标题进行去重。优先保留 `source` 为 "RSS" 或 "Twitter" 的条目。若来源优先级相同，则保留先遇到的条目。
    - 抓取网页原文以补充摘要或提取时间戳（按需，**Twitter来源会跳过此步**）
    - **智能摘要生成/处理 (目标最大长度: 150字符)**：
        - 优先使用RSS源或API提供的有效摘要（若存在且长度 > 10）。
        - 如无有效摘要，且抓取到足够内容 (`> 50字符`)，使用腾讯混元大模型生成摘要 (**Twitter来源跳过此步**)。
        - 如AI生成失败，尝试截断抓取到的网页纯文本内容作为备选摘要。
        - 如抓取失败或内容不足，尝试截断源提供的原始描述（如果存在）。
        - 如以上均失败，使用占位符 `[摘要无法生成：无内容或来源信息不足]`。
        - **长度控制**: 最终所有有效摘要（原始、AI生成、截断）都会被检查，超过150字符会被截断并添加 `...`。
- **AI驱动的最终总结**：
    - 使用DeepSeek AI模型对去重和处理后的信息列表进行最终归纳总结。
    - **优化Prompt**：指导Deepseek理解包含社交媒体信息，并合并内容相似的条目。
- **多渠道推送**：支持9种不同的推送渠道，包括企业微信、钉钉、飞书、Telegram等。
    - **备选推送**: 若所有配置的渠道推送失败，会尝试使用 `.env` 中配置的 `WEBHOOK_URL` 进行推送。
- **定制化配置**：可通过环境变量灵活配置信息源、推送渠道和AI模型参数。
- **科技热点筛选**：可选择只收集和推送科技相关热点 (目前主要影响热榜、摘要生成时的判断以及Deepseek总结)。
- **缓存机制**：支持**腾讯混元生成的摘要**缓存，提高运行效率（基于内容哈希）。
- **自动清理**：自动清理 `data/raw`, `data/filtered`, `data/merged`, `data/inputs`, `data/outputs`, `data/webhook`, `cache/summary` 目录中超过 **7天** 的旧数据和日志文件。

## 项目结构

```
├── cache/              # 缓存目录
│   └── summary/        # 存储腾讯混元生成的摘要缓存
├── config/             # 配置文件目录
│   ├── config.py       # 主要配置文件 (包含 SOURCE_NAME_MAP, RSS_FEEDS 等)
│   └── __init__.py
├── crawler/            # 数据爬取模块
│   ├── data_collector.py  # 热点、RSS、Twitter数据收集 (包括RSS内容预提取)
│   ├── rss_parser.py      # RSS条目解析辅助函数
│   └── web_crawler.py     # 网页内容爬取 (包括提取时间戳)
│   └── __init__.py
├── data/               # 数据存储目录 (默认被.gitignore忽略)
│   ├── filtered/       # 过滤掉过旧内容后的数据
│   ├── inputs/         # LLM 输入数据 (Deepseek)
│   ├── merged/         # 合并所有来源（热榜/RSS/Twitter）后的数据
│   ├── outputs/        # LLM 输出数据 (Deepseek)
│   ├── processed_output/ # 最终处理和去重后，准备给Deepseek总结的新闻列表
│   ├── raw/            # 原始热点数据
│   └── webhook/        # 推送内容和响应数据
├── llm_integration/    # 大语言模型集成模块
│   ├── deepseek_integration.py  # DeepSeek模型集成 (最终总结)
│   └── hunyuan_integration.py   # 腾讯混元模型集成 (单条摘要)
│   └── __init__.py
├── notification/       # 通知推送模块
│   ├── webhook_sender.py  # Webhook推送实现 (包括多种渠道)
│   └── __init__.py
├── processor/          # 数据处理模块
│   └── news_processor.py  # 新闻/信息处理 (网页抓取、时间戳提取、摘要生成/截断、缓存)
│   └── __init__.py
── tests/              # 测试代码目录
│   ├── test_all_news_sources.py       # 测试所有配置的热点API源和RSS源的数据收集和处理流程
│   ├── test_deepseek_timeout.py       # 测试Deepseek AI API的超时和重试机制
│   ├── test_full_data_collection.py   # 模拟完整主流程测试(不含推送)
│   ├── test_real_rss_processing.py    # 测试真实RSS源的处理流程
│   ├── test_rss_feeds.py              # 测试所有配置RSS源的可访问性和基础解析
│   ├── test_rss_parser.py             # 测试RSS条目解析函数
│   ├── test_rss_processing.py          # 单元测试新闻处理核心函数
│   ├── test_web_crawler.py            # 测试网页内容和时间戳提取功能
│   ├── test_webhook_detailed.py       # 详细测试所有推送渠道
│   ├── test_wechat_article.py         # 测试微信公众号文章内容提取
│   └── __init__.py                    # 测试包初始化文件
├── utils/              # 工具函数模块
│   └── utils.py        # 通用工具函数 (文件保存、清理等)
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
HUNYUAN_API_KEY="your_hunyuan_api_key"    # 腾讯混元大模型API密钥 (用于生成单条摘要，如果SKIP_CONTENT=false且来源非Twitter则可能需要)

# --- 推送渠道 (至少配置一种，或配置下面的 WEBHOOK_URL 作为备选) ---
# 以企业微信机器人为例
QYWX_KEY="your_qywx_key"
# 或其他渠道，如钉钉、飞书、Telegram等，参考 .env.example

# --- 通用 Webhook (可选，作为上述渠道失败时的备选) ---
WEBHOOK_URL="your_webhook_url"
```

### 4. (可选) 配置RSS源

编辑 `config/config.py` 文件中的 `RSS_FEEDS` 列表，添加你想订阅的RSS源。格式如下：

```python
RSS_FEEDS = [\n    {\"name\": \"科技博客A\", \"url\": \"https://example.com/tech/rss.xml\"},\n    {\"name\": \"公众号-XXX\", \"url\": \"https://example.com/weixin/rss.xml\"},\n    # ... 更多RSS源\n]\n
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
1.  **收集数据**: 获取热榜、RSS源内容（尝试预提取内容）、获取近2天的Twitter Feed。
2.  **初步过滤**: 筛选掉过旧的热榜内容（默认1天），筛选近24小时的推文。
3.  **合并数据**: 将热榜、RSS、过滤后的推文合并。
4.  **内容处理**: (如果 `SKIP_CONTENT=False`)
    *   遍历每个条目：
    *   **检查摘要**: 是否有源提供的有效摘要？
    *   **检查内容/时间戳**: 是否需要抓取网页来获取内容（如无有效摘要且无预提取内容）或时间戳？(**Twitter来源跳过抓取**)
    *   **抓取网页**: 如果需要，抓取网页获取HTML和纯文本内容。
    *   **提取时间戳**: 如果需要且抓取到HTML，尝试提取发布时间。
    *   **生成/选择摘要 (目标最大长度150)**:
        *   若有有效原始摘要，使用它。
        *   若无，且有足够内容（非Twitter），调用腾讯混元生成。
        *   若AI失败，截断抓取内容。
        *   若抓取失败，截断原始描述。
        *   若都无，使用占位符。
    *   **缓存摘要**: 缓存混元生成的摘要。
    *   **截断摘要**: 确保最终摘要不超过150字符。
5.  **去重**: 基于完全相同的标题去重，优先保留RSS/Twitter来源。
6.  **保存处理后数据**: 将最终列表保存到 `data/processed_output/` 目录下。
7.  **最终总结**: 将去重后的信息列表发送给Deepseek进行归纳总结。
8.  **推送结果**: 将Deepseek生成的总结通过配置的渠道推送。若失败，尝试使用 `WEBHOOK_URL` 推送。
9.  **清理**: 删除超过7天的旧数据和缓存文件。

### 命令行参数

(注意: 环境变量优先于命令行参数和 `config.py` 中的默认值)

```bash
# 只处理和总结科技相关内容
export TECH_ONLY=True
python hot_news_main.py

# 禁用腾讯混元摘要缓存 (强制重新生成)
export NO_CACHE=True
python hot_news_main.py

# 跳过内容处理步骤 (步骤4)，直接使用原始内容进行总结 (会影响去重前的摘要质量)
export SKIP_CONTENT=True
python hot_news_main.py

# 限制每个热榜来源只获取1条数据
export HOTSPOT_LIMIT=1
python hot_news_main.py
```

## 环境变量说明

### 基础配置

| 变量名 | 说明 | 默认值 (来自config.py) |
|-------|------|-------|
| `TECH_ONLY` | 是否只处理科技热点 (影响热榜源选择、摘要判断和Deepseek总结Prompt) | `False` |
| `NO_CACHE` | 是否禁用腾讯混元摘要缓存 | `False` |
| `SKIP_CONTENT` | 是否跳过内容处理步骤(抓取原文、生成/截断摘要)。设为True可加速，但摘要质量可能下降，且无需`HUNYUAN_API_KEY`。 | `False` |
| `BASE_URL` | 热点数据API基础URL (hotApi项目) | `https://api-hot.imsyy.top` |
| `MAX_WORKERS` | 内容处理（网页抓取、混元API调用）时的最大并发线程数 | `5` |
| `FILTER_DAYS` | 过滤多少天内的热榜内容 | `1` |
| `RSS_DAYS` | 获取RSS中最近几天的文章 (默认与`FILTER_DAYS`一致) | `1` |
| `HOTSPOT_LIMIT` | 每个热榜来源获取的热点数量限制 | `1` |

### RSS配置

| 变量名 | 说明 | 默认值 (来自config.py) |
|-------|------|-------|
| `RSS_URL` | 单个RSS源URL (**仅在 `config.py` 中 `RSS_FEEDS` 列表为空时生效**) | `None` |
| `RSS_FEEDS` | 在 `config/config.py` 中配置，包含名称和URL的字典列表 | `[]` (空列表) |

### API密钥配置

| 变量名 | 说明 | 是否必需 |
|-------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek AI API密钥 | **是** |
| `HUNYUAN_API_KEY` | 腾讯混元大模型API密钥 | **是** (除非`SKIP_CONTENT=True`) |
| `DEEPSEEK_API_URL` | DeepSeek API接口地址 (可选，覆盖默认) | 否 |
| `DEEPSEEK_MODEL_ID` | DeepSeek模型ID (可选，覆盖默认) | 否 |

### 推送渠道配置

(请参考 `.env.example` 获取所有支持的渠道和变量名。至少配置一种渠道，或配置下面的`WEBHOOK_URL`作为备选。)

| 变量名 (部分示例) | 说明 | 配置示例 |
|-------|------|--------|
| `QYWX_KEY` | 企业微信机器人key | `693axxx-xxxx-xxxx-xxxx-xxxxx` |
| `DD_BOT_TOKEN` & `DD_BOT_SECRET` | 钉钉机器人Token和Secret | `xxxxxxxx` & `SECxxxxxxxx` |
| `FSKEY` | 飞书机器人Key | `xxxxxxxxxxxxxxxx` |
| `TG_BOT_TOKEN` & `TG_USER_ID` | Telegram机器人Token和用户ID | `123:...` & `123456` |
| ... | 其他渠道 | ... |
| `WEBHOOK_URL` | 通用Webhook URL (可作为推送失败时的备选方案) | `https://hook.example.com/...` |

## 常见问题

### 1. 为什么有些摘要是空的或类似 \"[摘要无法生成：无内容或来源信息不足]\"?

可能的原因：
    - **来源无有效信息**: 原始API/RSS/推文就没有提供摘要或有效内容。
    - **网页抓取失败**: (非Twitter来源) 目标网站限制访问、结构复杂或已失效，导致无法获取用于生成摘要的内容。
    - **内容不足**: 抓取到的原文或原始描述太短（少于50字符），不足以生成有意义的摘要。
    - **腾讯混元API调用失败**: (非Twitter来源) API密钥错误、网络问题或API服务异常。
    - **Twitter来源**: Twitter推文默认不进行AI摘要生成，如果原文过长会被截断，如果原文为空则可能无摘要。

### 2. 为什么有些摘要被截断了 (以 \"...\" 结尾)?

程序会将所有最终使用的摘要（无论是原始提供、AI生成还是内容截断）限制在 **150个字符** 以内。如果超过这个长度，就会被截断并添加 `...`。

### 3. Twitter Feed 数据是如何获取和处理的?

*   数据源于 `https://raw.githubusercontent.com/tuber0613/x-kit/main/tweets/` 下按日期组织的JSON文件 (获取近2天)。
*   处理时，只保留发布时间在 **最近24小时内** 的推文。
*   推文的原始内容会作为初始 `desc` 字段，标题是截断后的推文内容。
*   **关键：程序会跳过为Twitter推文抓取网页内容和调用腾讯混元生成摘要的步骤。**
*   推文的 `desc` 如果超过150字符，会被截断。
*   在去重阶段，Twitter来源的内容享有较高优先级。
*   Deepseek已被告知要考虑Twitter来源的信息。

### 4. 去重逻辑是如何工作的？

*   发生在所有内容处理（摘要生成/截断）完成之后，调用Deepseek总结之前。
*   基于**完全相同**的 `title` 字段进行判断。
*   如果标题相同，会优先保留 `source` 为 "RSS" 或 "Twitter" 的条目。
*   如果来源优先级相同（例如都是RSS，或都不是优先来源），则保留**先添加到列表中的那个条目**。
*   Deepseek的Prompt也要求它进一步合并**内容相似但标题可能不同**的条目。

### 5. 如何添加或修改支持的热榜来源?

*   主要的热榜来源由 `BASE_URL` 指向的API (`https://api-hot.imsyy.top`) 提供。你需要查看该API的文档了解支持的来源标识符。
*   在 `config/config.py` 中的 `ALL_SOURCES` 或 `TECH_SOURCES` 列表中添加或移除这些标识符。
*   可以通过设置 `HOTSPOT_LIMIT` 环境变量控制每个来源获取几条。

### 6. 如何解决 Cloudflare 保护导致的 RSS 获取失败?

*   程序已使用 `cloudscraper` 库尝试模拟浏览器行为绕过简单的 Cloudflare 检查。
*   对于需要复杂验证（如JS挑战、验证码）的站点，`cloudscraper` 可能仍然失败。日志中会记录相关警告。
*   此外，程序会尝试从RSS Feed本身提取 `content:encoded` 等字段，如果成功，即使后续抓取失败也可能有内容。
*   目前没有完美的通用解决方案，可以尝试寻找该站点的其他RSS源或联系站点管理员。

## 测试说明

`tests/` 目录包含一系列用于验证项目各个核心功能的脚本：

*   **`test_all_news_sources.py`**: 对所有配置的热点API源和RSS源进行端到端的数据收集和初步处理测试，模拟 `hot_news_main.py` 的主要流程（不含总结和推送），并将各阶段数据保存到 `data/test_sources/` 目录。
*   **`test_deepseek_timeout.py`**: 专门测试 Deepseek AI 总结 API 的超时和重试机制。使用少量预定义数据调用API，记录尝试次数、耗时和最终结果，并将详细日志保存到 `data/tests/`。
*   **`test_full_data_collection.py`**: 模拟完整的 `hot_news_main.py` 流程（包括可选的摘要生成和 Deepseek 总结，但不推送），并将各阶段结果（原始、过滤、合并、处理、总结）保存到 `data/` 下的对应子目录。
*   **`test_real_rss_processing.py`**: 专注于测试从真实 RSS 源获取数据后的处理流程。获取配置的 RSS 文章，选取少量进行处理（网页抓取、摘要生成等），并打印详细的处理前后对比信息。
*   **`test_rss_feeds.py`**: 测试所有在 `config.py` 中配置的 RSS 源的可访问性和基础解析情况。检查 URL 是否可达，`feedparser` 是否能解析，并打印每个源的测试摘要和部分条目信息。
*   **`test_rss_parser.py`**: 专门测试 `crawler/rss_parser.py` 中的 `extract_rss_entry` 函数对特定 RSS 源（默认"机器之心"）的解析效果。打印原始条目结构和解析后的提取结果，用于验证解析逻辑。
*   **`test_rss_processing.py`**: 使用 `unittest` 和模拟（mocking）技术对 `processor/news_processor.py` 中的核心函数 `process_hotspot_with_summary` 进行单元测试，验证其在不同输入条件下（如是否已有摘要/内容）的逻辑分支和对依赖函数（抓取、AI摘要）的调用是否正确，也包含对缓存机制的测试。
*   **`test_web_crawler.py`**: 使用 `unittest` 测试 `crawler/web_crawler.py` 中的网页内容和时间戳提取功能。包含对依赖库导入、基本提取逻辑和已有内容时跳过抓取的测试。**特殊用法**：可通过命令行提供 URL (`python tests/test_web_crawler.py <url>`) 来快速测试对特定网页的抓取效果。
*   **`test_webhook_detailed.py`**: 详细测试 `notification/webhook_sender.py` 中的所有推送渠道。先尝试通过 `notify()` 统一推送，若失败则逐个调用各渠道的独立推送函数进行测试，并报告每个渠道的成功/失败状态。
*   **`test_wechat_article.py`**: 一个命令行工具，用于测试对**特定 URL**（尤其是微信公众号文章）的内容和发布时间提取。用法：`python tests/test_wechat_article.py "<url>"`。

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。