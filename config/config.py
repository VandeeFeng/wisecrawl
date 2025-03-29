#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件：存放各种变量值和配置信息
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API密钥
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
HUNYUAN_API_KEY = os.getenv('HUNYUAN_API_KEY')

# Webhook URL
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# API配置
BASE_URL = os.getenv('BASE_URL', 'https://api-hot.tuber.cc')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
DEEPSEEK_MODEL_ID = os.getenv('DEEPSEEK_MODEL_ID', 'ep-20250307234946-b2znq')

# RSS配置
RSS_URL = os.getenv('RSS_URL', 'https://wewe.tuber.cc/feeds/all.atom?limit=20')
RSS_DAYS = int(os.getenv('RSS_DAYS', '1'))

# RSS源列表
RSS_FEEDS = [
    {
        'name': 'OpenAI Blog',
        'url': 'https://openai.com/blog/rss.xml'
    },
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
        'name': '量子位',
        'url': 'https://www.qbitai.com/feed'
    },
    {
        'name': 'InfoQ',
        'url': 'https://www.infoq.cn/feed'
    },
    {
        'name': 'Twitter',
        'accounts': [
            {
                'name': 'Barsee',
                'url': 'https://rsshub.app/twitter/user/heyBarsee'
            },
            # {
            #     'name': 'Sam Altman',
            #     'url': 'https://rsshub.app/twitter/user/sama'
            # },
            # {
            #     'name': 'Anthropic',
            #     'url': 'https://rsshub.app/twitter/user/AnthropicAI'
            # },
            # {
            #     'name': 'AI at Meta',
            #     'url': 'https://rsshub.app/twitter/user/AIatMeta'
            # },
            # {
            #     'name': 'Google DeepMind',
            #     'url': 'https://rsshub.app/twitter/user/GoogleDeepMind'
            # },
            # {
            #     'name': 'Hugging Face',
            #     'url': 'https://rsshub.app/twitter/user/huggingface'
            # },
            # {
            #     'name': 'Pieter Abbeel',
            #     'url': 'https://rsshub.app/twitter/user/pabbeel'
            # },
            # {
            #     'name': 'Eliezer Yudkowsky',
            #     'url': 'https://rsshub.app/twitter/user/ESYudkowsky'
            # },
            # {
            #     'name': 'Ilya Sutskever',
            #     'url': 'https://rsshub.app/twitter/user/ilyasut'
            # },
            # {
            #     'name': 'Eric Schmidt',
            #     'url': 'https://rsshub.app/twitter/user/ericschmidt'
            # },
            # {
            #     'name': 'Hugo Larochelle',
            #     'url': 'https://rsshub.app/twitter/user/hugo_larochelle'
            # },
            # {
            #     'name': 'elvis',
            #     'url': 'https://rsshub.app/twitter/user/omarsar0'
            # },
            # {
            #     'name': 'Jim Fan',
            #     'url': 'https://rsshub.app/twitter/user/DrJimFan'
            # },
            # {
            #     'name': 'Fei-Fei Li',
            #     'url': 'https://rsshub.app/twitter/user/drfeifei'
            # },
            # {
            #     'name': 'Emad',
            #     'url': 'https://rsshub.app/twitter/user/EMostaque'
            # },
            # {
            #     'name': 'Sebastian Raschka',
            #     'url': 'https://rsshub.app/twitter/user/rasbt'
            # },
            # {
            #     'name': 'Lucas Beyer',
            #     'url': 'https://rsshub.app/twitter/user/giffmana'
            # },
            # {
            #     'name': 'Aakanksha Chowdhery',
            #     'url': 'https://rsshub.app/twitter/user/achowdhery'
            # },
            # {
            #     'name': 'Jeff Dean',
            #     'url': 'https://rsshub.app/twitter/user/JeffDean'
            # },
            # {
            #     'name': 'Michael Black',
            #     'url': 'https://rsshub.app/twitter/user/Michael_J_Black'
            # },
            # {
            #     'name': 'Oriol Vinyals',
            #     'url': 'https://rsshub.app/twitter/user/OriolVinyalsML'
            # },
            # {
            #     'name': 'Lilian Weng',
            #     'url': 'https://rsshub.app/twitter/user/lilianweng'
            # },
            # {
            #     'name': 'hardmaru',
            #     'url': 'https://rsshub.app/twitter/user/hardmaru'
            # },
            # {
            #     'name': 'Demis Hassabis',
            #     'url': 'https://rsshub.app/twitter/user/demishassabis'
            # },
            # {
            #     'name': 'Sara Hooker',
            #     'url': 'https://rsshub.app/twitter/user/sarahookr'
            # },
            # {
            #     'name': 'Jürgen Schmidhuber',
            #     'url': 'https://rsshub.app/twitter/user/SchmidhuberAI'
            # },
            # {
            #     'name': 'François Chollet',
            #     'url': 'https://rsshub.app/twitter/user/fchollet'
            # },
            # {
            #     'name': 'Yao Fu',
            #     'url': 'https://rsshub.app/twitter/user/Francis_YAO_'
            # },
            # {
            #     'name': 'OpenAI',
            #     'url': 'https://rsshub.app/twitter/user/OpenAI'
            # },
            # {
            #     'name': 'Andrew Ng',
            #     'url': 'https://rsshub.app/twitter/user/AndrewYNg'
            # },
            # {
            #     'name': 'Jay Hack',
            #     'url': 'https://rsshub.app/twitter/user/mathemagic1an'
            # },
            # {
            #     'name': 'John Nay',
            #     'url': 'https://rsshub.app/twitter/user/johnjnay'
            # },
            # {
            #     'name': 'LangChain',
            #     'url': 'https://rsshub.app/twitter/user/LangChainAI'
            # },
            # {
            #     'name': '歸藏',
            #     'url': 'https://rsshub.app/twitter/user/op7418'
            # },
            # {
            #     'name': '宝玉',
            #     'url': 'https://rsshub.app/twitter/user/dotey'
            # },
            # {
            #     'name': 'Lex Fridman',
            #     'url': 'https://rsshub.app/twitter/user/lexfridman'
            # },
            # {
            #     'name': 'roon',
            #     'url': 'https://rsshub.app/twitter/user/tszzl'
            # },
            # {
            #     'name': 'Suhail',
            #     'url': 'https://rsshub.app/twitter/user/Suhail'
            # },
            # {
            #     'name': 'Aaron Levie',
            #     'url': 'https://rsshub.app/twitter/user/levie'
            # },
        ]
    },
    {
        'name': '公众号',
        'url': RSS_URL
    }

]

# 其他配置
TITLE_LENGTH = int(os.getenv('TITLE_LENGTH', '20'))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '5'))
FILTER_DAYS = int(os.getenv('FILTER_DAYS', '1'))

# 科技相关的信息源列表
TECH_SOURCES = [
    # "bilibili",     # 含大量科技区UP主（评测/教程/极客）
    "zhihu",        # 科技类问答和专栏文章
    "sspai",        # 专注效率工具和科技应用
    "ithome",       # IT科技新闻门户
    "36kr",         # 科技创新创业资讯平台
    "juejin",       # 开发者技术社区
    "csdn",         # 专业技术博客平台
    "51cto",        # IT技术运维社区  
    "huxiu",        # 科技商业媒体
    "ifanr",        # 聚焦智能硬件的科技媒体
    # "coolapk",      # 安卓应用和科技产品讨论
    # "v2ex",         # 创意工作者技术社区
    # "hostloc",      # 服务器和网络技术交流
    # "hupu",         # 虎扑数码区（手机/电脑讨论）
    "guokr",        # 泛科学科普平台
    "hellogithub",  # GitHub开源项目推荐
    "nodeseek",     # 服务器和网络技术论坛
    "52pojie",      # 软件逆向技术社区
    # "ithome-xijiayi",# 免费软件/游戏资讯
    "zhihu-daily",  # 含科技类深度报道
    # "tieba",        # 百度贴吧（手机/电脑相关贴吧）
]

# 所有可用的信息源
ALL_SOURCES = [
    "bilibili",   # 哔哩哔哩
    "weibo",      # 微博
    "zhihu",      # 知乎
    "baidu",      # 百度
    "douyin",     # 抖音
    "kuaishou",   # 快手
    "tieba",      # 百度贴吧
    "sspai",      # 少数派
    "ithome",     # IT之家
    "toutiao",    # 今日头条
    "36kr",       # 36氪
    "juejin",     # 掘金
    "csdn",       # CSDN
    "51cto",      # 51CTO
    "huxiu",      # 虎嗅
    "ifanr",      # 爱范儿
    "coolapk",    # 酷安
    "hupu",       # 虎扑
    "v2ex",       # V2EX
    "hostloc",    # 全球主机交流
    "sina-news",  # 新浪新闻
    "netease-news", # 网易新闻
    "qq-news",    # 腾讯新闻
    "thepaper",   # 澎湃新闻
    "jianshu",    # 简书
    "guokr",      # 果壳
    "acfun",      # AcFun
    "douban-movie", # 豆瓣电影
    "douban-group", # 豆瓣讨论小组
    "zhihu-daily", # 知乎日报
    "ithome-xijiayi", # IT之家「喜加一」
    "ngabbs",     # NGA
    "hellogithub", # HelloGitHub
    "nodeseek",   # NodeSeek
    "miyoushe",   # 米游社
    "genshin",    # 原神
    "honkai",     # 崩坏3
    "starrail",   # 崩坏：星穹铁道
    "weread",     # 微信读书
    "lol",        # 英雄联盟
    "52pojie",    # 吾爱破解
]

# 添加源名称映射字典
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