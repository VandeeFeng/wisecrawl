import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', None)
CONTENT_MODEL_API_KEY = os.getenv('CONTENT_MODEL_API_KEY', None)

WEBHOOK_URL = os.getenv('WEBHOOK_URL', None)


BASE_URL_DEFAULT = "https://api-hot.imsyy.top/"
raw_base_url = os.getenv('BASE_URL', BASE_URL_DEFAULT)
# Clean the URL: remove comments and strip whitespace
BASE_URL = raw_base_url.split('#')[0].strip()

# --- Add RSS Feed Link Configuration ---
RSS_FEED_LINK_DEFAULT = "http://localhost:5173"
RSS_FEED_LINK = os.getenv('RSS_FEED_LINK', RSS_FEED_LINK_DEFAULT).rstrip('/') # Read from env, default, and remove trailing slash
# --- End RSS Feed Link Configuration ---

DEEPSEEK_API_URL_DEFAULT = "http://127.0.0.1:11434/v1/chat/completions"
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', DEEPSEEK_API_URL_DEFAULT)

DEEPSEEK_MODEL_ID_DEFAULT = "deepseek-r1:14b"
DEEPSEEK_MODEL_ID = os.getenv('DEEPSEEK_MODEL_ID', DEEPSEEK_MODEL_ID_DEFAULT)

CONTENT_MODEL_ID_DEFAULT = "qwen2.5:14b"
CONTENT_MODEL_ID = os.getenv('CONTENT_MODEL_ID', CONTENT_MODEL_ID_DEFAULT)

RSS_URL_DEFAULT = None
RSS_URL = os.getenv('RSS_URL', RSS_URL_DEFAULT)
RSS_DAYS = int(os.getenv('RSS_DAYS', '1'))

RSS_FEEDS = [
    {
      'name': 'Github Trending',
      'url': 'https://rsshub.rssforever.com/github/trending/daily/any'
    },
    {
      'name': 'Hacker News 近期最佳',
      'url': 'https://hnrss.org/best'
    },
    {
        'name': '阮一峰的网络日志',
        'url': 'http://www.ruanyifeng.com/blog/atom.xml'
    },
    {
        'name': 'Solidot',
        'url': 'https://www.solidot.org/index.rss'
    },
    # {
    #     'name': 'Hacker News',
    #     'url': 'https://news.ycombinator.com/rss'
    # },
    {
        'name': '机器之心',
        'url': 'https://www.jiqizhixin.com/rss'
    },
    {
        'name': '极客公园',
        'url': 'http://www.geekpark.net/rss'
    },
    {
        'name': 'Google DeepMind',
        'url': 'https://deepmind.google/blog/rss.xml'
    },
    {
        'name': 'V2ex 热门',
        'url': 'https://rsshub.rssforever.com/v2ex/topics/hot'
    },
    {
        'name': 'LINUX DO 今日热门',
        'url': 'https://r4l.deno.dev/https://linux.do/top.rss?period=daily'
    },

    {
        'name': 'Twitter',
        'accounts': [

            {
                 'name': '歸藏',
                 'url': 'https://rsshub.app/twitter/user/op7418'
             },
            {
                'name': '宝玉',
                'url': 'https://rsshub.app/twitter/user/dotey'
            },
            {
                'name': 'karminski-牙医',
                'url': 'https://rsshub.app/twitter/user/karminski3'
            },
            {
                'name': 'Geek',
                'url': 'https://rsshub.app/twitter/user/geekbb'
            },
            {
                'name': 'yihong0618',
                'url': 'https://rsshub.app/twitter/user/yihong0618'
            },
            {
                'name': '面条',
                'url': 'https://rsshub.app/twitter/user/miantiao_me'
            },
        ]
    },
    {
        'name': '公众号',
        'url': RSS_URL
    }

]

TITLE_LENGTH_DEFAULT = 20
TITLE_LENGTH = int(os.getenv('TITLE_LENGTH', str(TITLE_LENGTH_DEFAULT)))

MAX_WORKERS_DEFAULT = 5
MAX_WORKERS = int(os.getenv('MAX_WORKERS', str(MAX_WORKERS_DEFAULT)))

FILTER_DAYS_DEFAULT = 1
FILTER_DAYS = int(os.getenv('FILTER_DAYS', str(FILTER_DAYS_DEFAULT)))

TECH_SOURCES = [
    # "bilibili",     # 含大量科技区UP主（评测/教程/极客）
    # "zhihu",        # 科技类问答和专栏文章
    "sspai",        # 专注效率工具和科技应用
    # "ithome",       # IT科技新闻门户
    # "36kr",         # 科技创新创业资讯平台
    "juejin",       # 开发者技术社区
    # "csdn",         # 专业技术博客平台
    # "51cto",        # IT技术运维社区
    # "huxiu",        # 科技商业媒体
    "ifanr",        # 聚焦智能硬件的科技媒体
    # "coolapk",      # 安卓应用和科技产品讨论
    "v2ex",         # 创意工作者技术社区
    # "hostloc",      # 服务器和网络技术交流
    # "hupu",         # 虎扑数码区（手机/电脑讨论）
    "guokr",        # 泛科学科普平台
    "hellogithub",  # GitHub开源项目推荐
    # "nodeseek",     # 服务器和网络技术论坛
    # "52pojie",      # 软件逆向技术社区
    # "ithome-xijiayi",# 免费软件/游戏资讯
    "zhihu-daily",  # 含科技类深度报道
    # "tieba",        # 百度贴吧（手机/电脑相关贴吧）
]

# 所有可用的信息源
ALL_SOURCES = [
    "bilibili",   # 哔哩哔哩
    # "weibo",      # 微博
    "zhihu",      # 知乎
    # "baidu",      # 百度
    # "douyin",     # 抖音
    # "kuaishou",   # 快手
    # "tieba",      # 百度贴吧
    "sspai",      # 少数派
    # "ithome",     # IT之家
    # "toutiao",    # 今日头条
    "36kr",       # 36氪
    # "juejin",     # 掘金
    # "csdn",       # CSDN
    #"51cto",      # 51CTO
    # "huxiu",      # 虎嗅
    "ifanr",      # 爱范儿
    # "coolapk",    # 酷安
    # "hupu",       # 虎扑
    # "v2ex",       # V2EX
    # "hostloc",    # 全球主机交流
    # "sina-news",  # 新浪新闻
    # "netease-news", # 网易新闻
    # "qq-news",    # 腾讯新闻
    "thepaper",   # 澎湃新闻
    # "jianshu",    # 简书
    "guokr",      # 果壳
    # "acfun",      # AcFun
    # "douban-movie", # 豆瓣电影
    # "douban-group", # 豆瓣讨论小组
    "zhihu-daily", # 知乎日报
    # "ithome-xijiayi", # IT之家「喜加一」
    # "ngabbs",     # NGA
    "hellogithub", # HelloGitHub
    # "nodeseek",   # NodeSeek
    # "miyoushe",   # 米游社
    # "genshin",    # 原神
    # "honkai",     # 崩坏3
    # "starrail",   # 崩坏：星穹铁道
    # "weread",     # 微信读书
    # "lol",        # 英雄联盟
    # "52pojie",    # 吾爱破解
]

SOURCE_NAME_MAP = {
    "bilibili": "哔哩哔哩",
    "weibo": "微博",
    "zhihu": "知乎",
    "baidu": "百度",
    "douyin": "抖音",
    "kuaishou": "快手",
    "tieba": "百度贴吧",
    "sspai": "少数派",
    "ithome": "IT之家",
    "toutiao": "今日头条",
    "36kr": "36氪",
    "juejin": "掘金",
    "csdn": "CSDN",
    "51cto": "51CTO",
    "huxiu": "虎嗅",
    "ifanr": "爱范儿",
    "coolapk": "酷安",
    "hupu": "虎扑",
    "v2ex": "V2EX",
    "hostloc": "全球主机交流",
    "sina-news": "新浪新闻",
    "netease-news": "网易新闻",
    "qq-news": "腾讯新闻",
    "thepaper": "澎湃新闻",
    "jianshu": "简书",
    "guokr": "果壳",
    "acfun": "AcFun",
    "douban-movie": "豆瓣电影",
    "douban-group": "豆瓣讨论小组",
    "zhihu-daily": "知乎日报",
    "ithome-xijiayi": "IT之家喜加一",
    "ngabbs": "NGA",
    "hellogithub": "HelloGitHub",
    "nodeseek": "NodeSeek",
    "miyoushe": "米游社",
    "genshin": "原神",
    "honkai": "崩坏3",
    "starrail": "崩坏：星穹铁道",
    "weread": "微信读书",
    "lol": "英雄联盟",
    "52pojie": "吾爱破解",
}
