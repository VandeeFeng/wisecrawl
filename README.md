# 热点新闻收集与推送工具 (Hot News Daily Push)

这是一个自动收集各大平台热点新闻，并通过多种渠道推送热点摘要的工具。它支持从多个信息源获取热点数据，使用AI模型生成摘要，并通过多种渠道（如企业微信、钉钉、飞书等）推送每日热点早报。

## 功能特点

- **多源数据收集**：支持从30+个平台（如微博、知乎、百度、抖音等）收集热点数据
- **智能摘要生成**：使用DeepSeek和腾讯混元大模型对热点内容进行摘要和归类
- **多渠道推送**：支持9种不同的推送渠道，包括企业微信、钉钉、飞书、Telegram等
- **定制化配置**：可通过环境变量灵活配置信息源、推送渠道和AI模型参数
- **科技热点筛选**：可选择只收集和推送科技相关热点
- **RSS源集成**：支持从RSS源获取额外的热点文章

## 项目结构

```
├── cache/              # 缓存目录，存储摘要缓存等
├── config/             # 配置文件目录
│   └── config.py       # 主要配置文件
├── crawler/            # 数据爬取模块
│   ├── data_collector.py  # 热点数据收集
│   └── web_crawler.py     # 网页内容爬取
├── data/               # 数据存储目录
│   ├── filtered/       # 过滤后的热点数据
│   ├── inputs/         # AI模型输入数据
│   ├── merged/         # 合并处理后的数据
│   ├── outputs/        # AI模型输出数据
│   └── webhook/        # 推送内容和响应数据
├── llm_integration/    # AI模型集成模块
│   ├── deepseek_integration.py  # DeepSeek模型集成
│   └── hunyuan_integration.py   # 腾讯混元模型集成
├── notification/       # 通知推送模块
│   ├── notify.py       # 通用通知函数
│   └── webhook_sender.py  # Webhook推送实现
├── processor/          # 数据处理模块
│   └── news_processor.py  # 新闻处理函数
├── utils/              # 工具函数模块
│   └── utils.py        # 通用工具函数
├── .env                # 环境变量配置文件（需自行创建）
├── .env.example        # 环境变量示例文件
├── hot_news.py         # 旧版主程序
├── hot_news_main.py    # 主程序入口
├── requirements.txt    # 依赖项列表
└── test_webhook_detailed.py  # Webhook测试脚本
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

编辑`.env`文件，配置以下必要参数：

```
***REMOVED***
DEEPSEEK_API_KEY=your_deepseek_api_key  # DeepSeek AI API密钥
HUNYUAN_API_KEY=your_hunyuan_api_key    # 腾讯混元大模型API密钥

# 至少配置一种推送方式
WEBHOOK_URL=your_webhook_url  # 通用Webhook URL
```

### 4. 配置推送渠道

在`.env`文件中配置你需要的推送渠道，例如：

```
# 企业微信机器人
QYWX_KEY=your_qywx_key

# 钉钉机器人
DD_BOT_SECRET=your_dd_bot_secret
DD_BOT_TOKEN=your_dd_bot_token

***REMOVED***
FSKEY=your_fskey
```

完整的推送渠道配置请参考`.env.example`文件。

## 使用方法

### 运行主程序

```bash
python hot_news_main.py
```

### 使用命令行参数

```bash
# 只收集科技相关热点
python hot_news_main.py --tech-only

# 不使用缓存
python hot_news_main.py --no-cache

# 跳过内容处理（不获取网页内容和摘要）
python hot_news_main.py --skip-content
```

### 测试推送功能

```bash
python test_webhook_detailed.py
```

## 环境变量说明

### 基础配置

| 变量名 | 说明 | 默认值 |
|-------|------|-------|
| `TECH_ONLY` | 是否只收集科技热点 | `False` |
| `NO_CACHE` | 是否禁用缓存 | `False` |
| `SKIP_CONTENT` | 是否跳过内容处理 | `False` |
| `BASE_URL` | 热点数据API基础URL | `https://api-hot.tuber.cc` |
| `MAX_WORKERS` | 最大并发工作线程数 | `5` |
| `FILTER_DAYS` | 过滤多少天内的热点 | `1` |

##***REMOVED***

| 变量名 | 说明 | 是否必需 |
|-------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek AI API密钥 | 是 |
| `HUNYUAN_API_KEY` | 腾讯混元大模型API密钥 | 是（除非设置`SKIP_CONTENT=True`）|
| `DEEPSEEK_API_URL` | DeepSeek API接口地址 | 否 |
| `DEEPSEEK_MODEL_ID` | DeepSeek模型ID | 否 |

### 推送渠道配置

| 变量名 | 说明 | 配置示例 |
|-------|------|--------|
| `WEBHOOK_URL` | 通用Webhook URL | `https://example.com/webhook` |
| `QYWX_KEY` | 企业微信机器人key | `693axxx-xxxx-xxxx-xxxx-xxxxx` |
| `DD_BOT_TOKEN` | 钉钉机器人Token | `xxxxxxxxxxxxxxxx` |
| `DD_BOT_SECRET` | 钉钉机器人Secret | `SECxxxxxxxxxxxxxxxx` |
| `FSKEY` | 飞书机器人Key | `xxxxxxxxxxxxxxxx` |
| `TG_BOT_TOKEN` | Telegram机器人Token | `123456789:ABCDEF` |
| `TG_USER_ID` | Telegram用户ID | `123456789` |
| `BARK_PUSH` | Bark推送URL | `https://api.day.app/xxxxxxxx` |
| `PUSH_PLUS_TOKEN` | PushPlus Token | `xxxxxxxxxxxxxxxx` |
| `PUSH_KEY` | Server酱Key | `xxxxxxxxxxxxxxxx` |
| `QYWX_AM` | 企业微信应用参数 | `corpid,corpsecret,touser,agentid,media_id` |

## 推送渠道测试

项目提供了一个专门的测试脚本`test_webhook_detailed.py`，用于测试各种推送渠道是否正常工作。运行此脚本将：

1. 显示当前配置的所有推送渠道
2. 测试所有已配置的推送渠道
3. 如果综合测试失败，会单独测试每个渠道
4. 显示测试结果和生成的推送内容文件

```bash
python test_webhook_detailed.py
```

## 常见问题

### 1. 如何只获取科技相关热点？

设置环境变量`TECH_ONLY=True`或使用命令行参数`--tech-only`。

### 2. 如何解决API密钥配置问题？

确保在`.env`文件中正确配置了`DEEPSEEK_API_KEY`和`HUNYUAN_API_KEY`。如果不需要内容处理，可以设置`SKIP_CONTENT=True`来跳过对`HUNYUAN_API_KEY`的需求。

### 3. 推送失败怎么办？

运行`test_webhook_detailed.py`脚本测试各个推送渠道，检查配置是否正确。查看`data/webhook/`目录下的响应文件，了解失败原因。

### 4. 如何自定义推送内容格式？

修改`notification/webhook_sender.py`文件中的`format_content`函数来自定义推送内容的格式。

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。