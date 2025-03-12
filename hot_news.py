#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 在文件顶部添加必要的导入
import os
import hashlib
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import requests
import json
import time
import argparse
from datetime import datetime, timedelta
import logging
import os
import sys
import feedparser  # 新增：用于解析RSS/Atom feed
import asyncio
from concurrent.futures import ThreadPoolExecutor
from langchain_community.document_loaders import WebBaseLoader
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import re

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    "coolapk",      # 安卓应用和科技产品讨论
    "v2ex",         # 创意工作者技术社区
    "hostloc",      # 服务器和网络技术交流
    "hupu",         # 虎扑数码区（手机/电脑讨论）
    "guokr",        # 泛科学科普平台
    "hellogithub",  # GitHub开源项目推荐
    "nodeseek",     # 服务器和网络技术论坛
    "52pojie",      # 软件逆向技术社区
    "ithome-xijiayi",# 免费软件/游戏资讯
    "zhihu-daily",  # 含科技类深度报道
    "tieba",        # 百度贴吧（手机/电脑相关贴吧）
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

def save_hotspots_to_jsonl(hotspots, directory="data"):
    """
    将热点数据保存为JSONL格式，按日期组织，使用相对路径
    """
    try:
        # 确保目录存在
        os.makedirs(directory, exist_ok=True)
        
        # 生成文件名，使用当前日期
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H-%M-%S")
        filename = os.path.join(directory, f"hotspots_{today}_{timestamp}.jsonl")
        
        # 写入JSONL文件
        with open(filename, 'w', encoding='utf-8') as f:
            for item in hotspots:
                # 添加时间戳
                item_with_timestamp = item.copy()
                item_with_timestamp['saved_at'] = datetime.now().isoformat()
                f.write(json.dumps(item_with_timestamp, ensure_ascii=False) + '\n')
        
        logger.info(f"已将 {len(hotspots)} 条热点数据保存至 {filename}")
        return filename
    except Exception as e:
        logger.error(f"保存热点数据时发生错误: {str(e)}")
        return None

# 添加缓存相关函数
def get_content_hash(content):
    """
    计算内容的哈希值，用于缓存标识
    """
    if not content:
        return None
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_summary_cache(cache_dir="cache/summary"):
    """
    加载摘要缓存
    """
    try:
        cache_path = Path(cache_dir) / "summary_cache.pkl"
        if not cache_path.exists():
            return {}
        
        with open(cache_path, 'rb') as f:
            cache = pickle.load(f)
            logger.info(f"已加载摘要缓存，包含 {len(cache)} 条记录")
            return cache
    except Exception as e:
        logger.warning(f"加载摘要缓存失败: {str(e)}")
        return {}

def save_summary_cache(cache, cache_dir="cache/summary"):
    """
    保存摘要缓存
    """
    try:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        with open(cache_path / "summary_cache.pkl", 'wb') as f:
            pickle.dump(cache, f)
            logger.info(f"已保存摘要缓存，共 {len(cache)} 条记录")
    except Exception as e:
        logger.warning(f"保存摘要缓存失败: {str(e)}")


def check_base_url(base_url):
    """
    检查 BASE_URL 是否可访问
    """
    try:
        response = requests.get(f"{base_url}/bilibili?limit=5", timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 200:
            logger.info(f"BASE_URL 检查通过: {base_url}")
            return True
        else:
            logger.error(f"BASE_URL 返回错误: {data}")
            return False
    except Exception as e:
        logger.error(f"BASE_URL 检查失败: {str(e)}")
        return False

def fetch_hotspot(source, base_url):
    """
    从指定源获取热点数据
    """
    try:
        url = f"{base_url}/{source}?limit=10"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 200:
            return data.get("data", [])
        else:
            logger.error(f"获取 {source} 数据失败: {data.get('message', '未知错误')}")
            return []
    except Exception as e:
        logger.error(f"获取 {source} 数据时发生错误: {str(e)}")
        return []

def collect_all_hotspots(sources, base_url):
    """
    收集所有指定源的热点数据
    """
    all_hotspots = []
    
    for source in sources:
        logger.info(f"正在获取 {source} 的热点数据...")
        hotspots = fetch_hotspot(source, base_url)
        
        for item in hotspots:
            # 确保每个热点都有标题和链接
            if "title" in item and "url" in item:
                # 构建热点数据，保留desc字段
                hotspot_data = {
                    "title": item["title"],
                    "url": item["url"],
                    "source": source,
                    "hot": item.get("hot", ""),
                    "time": item.get("time", ""),
                    "timestamp": item.get("timestamp", ""),
                }
                
                # 如果有摘要，保留摘要
                if "desc" in item and item["desc"]:
                    hotspot_data["desc"] = item["desc"]
                    
                all_hotspots.append(hotspot_data)
    
    logger.info(f"共收集到 {len(all_hotspots)} 条热点数据")
    return all_hotspots

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
def format_title_for_display(title, source, max_length=30):
    """
    格式化标题，确保长度一致，适配手机宽度
    """
    # 计算标题最大长度（考虑到后面要加上来源）
    source_part = f" - {source}"
    title_max_length = max_length - len(source_part)
    
    # 如果标题太长，截断并添加省略号
    if len(title) > title_max_length:
        title = title[:title_max_length-1] + "…"
    
    # 返回格式化后的标题
    return f"{title}{source_part}"
# 修改fetch_webpage_content函数，返回原始HTML内容
def fetch_webpage_content(url, timeout=10, max_retries=3):
    """
    获取网页内容，返回处理后的文本内容和原始HTML
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 设置更多选项以提高稳定性
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout, verify=False)
            response.raise_for_status()
            
            # 获取原始HTML内容
            html_content = response.text
            
            # 使用BeautifulSoup处理HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取文本内容
            text_content = soup.get_text(separator=' ', strip=True)
            
            # 预处理文本内容
            processed_content = preprocess_webpage_content(text_content)
            
            logger.info(f"获取到网页内容: {url}, 原始HTML长度: {len(html_content)}, 处理后文本长度: {len(processed_content)} 字符")
            
            return processed_content, html_content
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"获取网页内容失败: {url}, 错误: {str(e)}，5秒后重试 ({retry_count}/{max_retries})...")
                time.sleep(5)
            else:
                logger.error(f"获取网页内容失败: {url}, 错误: {str(e)}")
                return "", ""

def preprocess_webpage_content(content):
    """
    预处理网页内容，去除无关内容，提取核心文本
    """
    if not content:
        return ""
    
    # 1. 去除多余空白字符
    content = ' '.join(content.split())
    
    # 2. 去除常见的网页噪音
    noise_patterns = [
        r'版权所有.*?保留所有权利',
        r'Copyright.*?Reserved',
        r'免责声明.*?',
        r'隐私政策.*?',
        r'登录.*?注册',
        r'关注我们.*?',
        r'点击查看.*?',
        r'相关阅读.*?',
        r'猜你喜欢.*?',
        r'广告.*?',
        r'评论.*?',
    ]
    
    import re
    for pattern in noise_patterns:
        content = re.sub(pattern, ' ', content, flags=re.IGNORECASE)
    
    # 3. 如果内容太长，保留前2000字符（考虑到后续会截断）
    if len(content) > 3000:
        # 记录截断信息
        logger.info(f"内容过长，从 {len(content)} 字符截断至 3000 字符")
        
        # 尝试在句子边界截断
        sentences = re.split(r'[.。!！?？;；]', content[:3000])
        if len(sentences) > 1:
            # 保留完整句子
            content = '.'.join(sentences[:-1]) + '.'
        else:
            content = content[:3000]
    
    return content
# 修改summarize_with_tencent_hunyuan函数，添加缓存功能
def summarize_with_tencent_hunyuan(content, api_key, max_retries=3, use_cache=True):
    """
    使用腾讯混元turbo-S模型对内容进行概述总结
    返回JSON格式，包含摘要和科技相关性判断
    支持缓存机制，避免重复处理相同内容
    """
    if not content or len(content.strip()) < 50:
        logger.warning(f"内容过短或为空，跳过摘要生成: {content[:50]}...")
        return {"summary": "", "is_tech": False}
    
    # 计算内容哈希值用于缓存
    content_hash = get_content_hash(content[:2000])  # 只对前2000字符计算哈希
    
    # 如果启用缓存，尝试从缓存中获取结果
    if use_cache and content_hash:
        # 加载缓存
        summary_cache = load_summary_cache()
        
        # 检查缓存中是否有对应的结果
        if content_hash in summary_cache:
            cached_result = summary_cache[content_hash]
            logger.info(f"从缓存中获取摘要: {cached_result['summary'][:30]}...")
            return cached_result
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 记录要发送的内容长度
            logger.info(f"发送至混元模型的内容长度: {len(content[:2000])} 字符")
            
            # 创建LLM实例，添加正确的base_url
            llm = ChatOpenAI(
                model="hunyuan-turbos-latest",  # 使用hunyuan-turboS模型
                temperature=0.3,
                api_key=api_key,
                max_tokens=150,
                base_url="https://api.hunyuan.cloud.tencent.com/v1"  # 添加混元API的base_url
            )
            
            # 创建提示模板，要求返回JSON格式
            prompt = PromptTemplate(
                input_variables=["content"],
                template="""请对以下新闻内容进行简洁概述，并判断是否与科技相关（包括AI、互联网、软件、硬件、电子产品等）。
                
                    新闻内容：
                    {content}

                    请以JSON格式返回，包含以下字段：
                    1. summary: 新闻摘要，不超过50个字
                    2. is_tech: 布尔值，表示是否与科技相关

                    只返回JSON格式，不要有任何额外说明。
                    """
            )
            
            # 创建LLMChain
            chain = LLMChain(llm=llm, prompt=prompt)
            
            # 调用模型
            response = chain.invoke({"content": content[:2000]})  # 限制输入长度
            
            result_text = response.get("text", "").strip()
            
            # 尝试解析JSON
            try:
                # 如果返回的不是纯JSON，尝试提取JSON部分
                if not result_text.startswith("{"):
                    import re
                    json_match = re.search(r'({.*})', result_text, re.DOTALL)
                    if json_match:
                        result_text = json_match.group(1)
                
                result = json.loads(result_text)
                
                # 确保结果包含必要的字段
                if "summary" not in result:
                    result["summary"] = ""
                if "is_tech" not in result:
                    result["is_tech"] = False
                
                logger.info(f"生成的摘要: {result['summary']}, 科技相关: {result['is_tech']}")
                
                # 如果启用缓存，将结果保存到缓存
                if use_cache and content_hash:
                    summary_cache = load_summary_cache()
                    summary_cache[content_hash] = result
                    save_summary_cache(summary_cache)
                
                return result
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回文本作为摘要
                logger.warning(f"JSON解析失败，使用原始文本: {result_text}")
                result = {"summary": result_text[:50], "is_tech": False}
                
                # 如果启用缓存，将结果保存到缓存
                if use_cache and content_hash:
                    summary_cache = load_summary_cache()
                    summary_cache[content_hash] = result
                    save_summary_cache(summary_cache)
                
                return result
        
        except Exception as e:
            logger.error(f"调用腾讯混元模型失败: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"5秒后重试 ({retry_count}/{max_retries})...")
                time.sleep(5)
            else:
                break
    
    return {"summary": "", "is_tech": False}


def extract_publish_time_from_html(html_content, url):
    """
    从HTML内容中提取发布时间
    支持多种常见的时间格式和HTML结构
    """
    if not html_content:
        return None
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. 尝试从meta标签中提取时间
        meta_tags = [
            soup.find('meta', property='article:published_time'),
            soup.find('meta', property='og:published_time'),
            soup.find('meta', property='publish_date'),
            soup.find('meta', itemprop='datePublished'),
            soup.find('meta', name='pubdate'),
            soup.find('meta', name='publishdate'),
            soup.find('meta', name='date')
        ]
        
        for tag in meta_tags:
            if tag and tag.get('content'):
                try:
                    return date_parser.parse(tag.get('content'))
                except:
                    pass
        
        # 2. 尝试从time标签中提取
        time_tags = soup.find_all('time')
        for time_tag in time_tags:
            datetime_attr = time_tag.get('datetime')
            if datetime_attr:
                try:
                    return date_parser.parse(datetime_attr)
                except:
                    pass
        
        # 3. 针对特定网站的自定义提取逻辑
        if 'juejin.cn' in url:
            # 掘金网站的时间提取
            time_elements = soup.find_all('time', class_='time')
            for time_element in time_elements:
                if time_element.get('datetime'):
                    try:
                        return date_parser.parse(time_element.get('datetime'))
                    except:
                        pass
        
        # 4. 尝试从常见的日期格式中提取
        date_patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # 2024-03-08 12:34:56
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # 2024-03-08T12:34:56
            r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}',        # 2024/03/08 12:34
            r'\d{4}年\d{1,2}月\d{1,2}日 \d{1,2}:\d{1,2}',  # 2024年3月8日 12:34
            r'\d{4}年\d{1,2}月\d{1,2}日',            # 2024年3月8日
            r'\d{4}-\d{2}-\d{2}'                     # 2024-03-08
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                try:
                    return date_parser.parse(matches[0])
                except:
                    pass
        
        logger.debug(f"无法从HTML内容中提取发布时间: {url}")
        return None
    
    except Exception as e:
        logger.warning(f"提取发布时间时发生错误: {str(e)}, URL: {url}")
        return None


# 修改process_hotspot_with_summary函数，处理从HTML中提取的时间
# 修改process_hotspot_with_summary函数，传递use_cache参数
# 修改process_hotspot_with_summary函数，添加更新merged文件的功能
async def process_hotspot_with_summary(hotspots, hunyuan_api_key, max_workers=5, tech_only=False, use_cache=True):
    """
    异步处理热点数据，获取网页内容并生成摘要
    优先使用API返回的摘要，没有摘要时才调用混元模型
    同时尝试从网页内容中提取发布时间
    如果tech_only为True，则只保留科技相关的内容
    支持缓存机制，避免重复处理相同内容
    处理后直接更新merged文件
    """
    enhanced_hotspots = []
    
    # 获取原始merged文件路径
    merged_file_path = None
    if hotspots and len(hotspots) > 0 and "saved_at" in hotspots[0]:
        saved_time = hotspots[0]["saved_at"]
        try:
            # 从saved_at字段提取时间戳
            dt = datetime.fromisoformat(saved_time.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H-%M-%S")
            merged_file_path = os.path.join("data", "merged", f"hotspots_{date_str}_{time_str}.jsonl")
            logger.info(f"找到原始merged文件: {merged_file_path}")
        except Exception as e:
            logger.warning(f"无法从saved_at提取时间戳: {str(e)}")
    
    async def process_single_item(item):
        url = item["url"]
        logger.info(f"开始处理: {item['title']} ({url})")
        
        # 检查是否已有摘要
        has_summary = item.get("desc") and len(item.get("desc", "").strip()) > 20
        
        # 检查是否已有时间戳
        has_timestamp = item.get("timestamp") or item.get("time", "")
        
        # 如果同时有摘要和时间戳，直接使用
        if has_summary and has_timestamp:
            logger.info(f"使用API返回的摘要和时间戳: {item['title']}")
            # 默认不知道是否科技相关，设为True以避免过滤
            return {**item, "content": "", "summary": item["desc"], "is_tech": True, "is_processed": True}
        
        # 获取网页内容和原始HTML
        content, html_content = fetch_webpage_content(url)
        summary_result = {"summary": "", "is_tech": False}
        
        # 如果没有时间戳，尝试从HTML中提取
        if not has_timestamp and html_content:
            publish_time = extract_publish_time_from_html(html_content, url)
            if publish_time:
                logger.info(f"从HTML中提取到发布时间: {publish_time}, 标题: {item['title']}")
                # 添加提取到的时间戳
                item["extracted_time"] = publish_time.isoformat()
                item["timestamp"] = int(publish_time.timestamp() * 1000)  # 转换为毫秒级时间戳
        
        # 如果没有摘要但有内容，生成摘要
        if not has_summary and content:
            summary_result = summarize_with_tencent_hunyuan(content, hunyuan_api_key, use_cache=use_cache)
        elif has_summary:
            # 如果已有摘要，默认设置为科技相关（避免过滤）
            summary_result = {"summary": item["desc"], "is_tech": True}
            
        result = {
            **item, 
            "content": content, 
            "summary": summary_result["summary"],
            "is_tech": summary_result["is_tech"],
            "is_processed": True  # 添加处理标记
        }
        
        logger.info(f"处理完成: {item['title']}, 摘要长度: {len(result['summary'])}, 科技相关: {result['is_tech']}")
        return result
    
    # 使用线程池执行网页内容获取和摘要生成
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                lambda i=i: process_single_item(i)
            )
            for i in hotspots
        ]
        
        completed_tasks = await asyncio.gather(*tasks)
        for completed_task in completed_tasks:
            result = await completed_task
            # 如果tech_only为True，只保留科技相关的内容
            if not tech_only or result.get("is_tech", False):
                enhanced_hotspots.append(result)
    
    # 记录处理结果统计
    with_summary = sum(1 for item in enhanced_hotspots if item.get("summary"))
    with_timestamp = sum(1 for item in enhanced_hotspots if item.get("timestamp") or item.get("time") or item.get("extracted_time"))
    tech_related = sum(1 for item in enhanced_hotspots if item.get("is_tech", False))
    
    logger.info(f"热点处理完成: 总计 {len(enhanced_hotspots)} 条, 成功生成摘要 {with_summary} 条, 有时间戳 {with_timestamp} 条, 科技相关 {tech_related} 条")
    
    # 如果找到了原始merged文件，直接更新
    if merged_file_path and os.path.exists(merged_file_path):
        try:
            # 创建一个ID到处理结果的映射
            processed_items = {item["url"]: item for item in enhanced_hotspots}
            
            # 读取原始文件并更新
            updated_lines = []
            with open(merged_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        url = item.get("url", "")
                        if url in processed_items:
                            # 更新已处理的项目
                            updated_item = processed_items[url]
                            # 只保留需要的字段，不包括content等大字段
                            updated_item_clean = {k: v for k, v in updated_item.items() 
                                               if k not in ["content"]}
                            updated_lines.append(json.dumps(updated_item_clean, ensure_ascii=False))
                        else:
                            # 保持原有项目不变
                            updated_lines.append(line.strip())
            
            # 写回文件
            with open(merged_file_path, 'w', encoding='utf-8') as f:
                for line in updated_lines:
                    f.write(line + '\n')
            
            logger.info(f"已更新merged文件: {merged_file_path}")
        except Exception as e:
            logger.error(f"更新merged文件失败: {str(e)}")
    
    return enhanced_hotspots
    

# 修改summarize_with_deepseek函数，添加保存JSON数据的功能
def summarize_with_deepseek(hotspots, api_key, api_url=None, model_id=None, max_retries=3, tech_only=False):
    """
    使用Deepseek API对热点进行汇总归类，支持重试
    根据tech_only参数使用不同的prompt
    """
    if api_url is None:
        api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    if model_id is None:
        model_id = "ep-20250220195531-ds6nm"
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 简化输入数据，只传递必要信息，但包含摘要
            simplified_hotspots = []
            for idx, item in enumerate(hotspots):
                source_name = SOURCE_NAME_MAP.get(item['source'], item['source'])
                simplified_hotspots.append({
                    "id": idx,
                    "title": item['title'],
                    "source": source_name,
                    "summary": item.get('summary', '')  # 添加摘要信息
                })
            
            # 将完整数据转换为字典以便后续查找
            hotspot_dict = {idx: item for idx, item in enumerate(hotspots)}
            
            # 转换为JSON格式的输入
            hotspot_json = json.dumps(simplified_hotspots, ensure_ascii=False)
            
            # 保存输入的JSON数据，使用相对路径
            save_directory = os.path.join("data", "inputs")
            os.makedirs(save_directory, exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%H-%M-%S")
            input_filename = os.path.join(save_directory, f"deepseek_input_{today}_{timestamp}.json")
            with open(input_filename, 'w', encoding='utf-8') as f:
                f.write(hotspot_json)
            logger.info(f"已保存Deepseek输入数据至 {input_filename}")
            
            # 根据tech_only参数选择不同的prompt
            if tech_only:
                prompt = f"""
                以下是今日科技热点新闻列表（JSON格式），每个来源均已按照热榜排序，部分新闻包含内容摘要：
                {hotspot_json}
                请总结出10条最重要的科技新闻，优先选择AI相关新闻，去除重复和无关内容。AI相关新闻排序优先靠前，公众号的文章权重更高，其余按重要性排序。
                你需要将相似的新闻合并为一条，并提供一个直观简洁的标题，需要讲清楚新闻内容不要太泛化（不超过30个字）。
                相关新闻的ID列表最多选择其中4条（取最典型的），超过数量不需要全部给出。
                如果有摘要信息，请参考摘要提供更准确的标题。
                
                请以JSON格式返回结果，格式如下：
                ```json
                [
                  {{
                    "title": "新闻标题",
                    "related_ids": [相关新闻的ID列表]
                  }},
                  ...
                ]
                ```
                
                只返回JSON数据，不要有任何额外说明。
                """
            else:
                prompt = f"""
                以下是今日热点新闻列表（JSON格式），每个来源均已按照热榜排序，部分新闻包含内容摘要：
                {hotspot_json}
                请总结出10条最重要的热点新闻，优先选择科技和AI相关新闻，但也要包含其他领域（如社会、娱乐、体育等）的重要新闻，去除重复内容。
                你需要将相似的新闻合并为一条，并提供一个直观简洁的标题，需要讲清楚新闻内容不要太泛化（不超过30个字）。
                相关新闻的ID列表最多选择其中4条（取最典型的），超过数量不需要全部给出。
                如果有摘要信息，请参考摘要提供更准确的标题。
                
                请以JSON格式返回结果，格式如下：
                ```json
                [
                  {{
                    "title": "新闻标题",
                    "related_ids": [相关新闻的ID列表]
                  }},
                  ...
                ]
                ```
                
                只返回JSON数据，不要有任何额外说明。
                """
            
            # 调用Deepseek API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "你是一个专业的新闻编辑助手，擅长归纳总结热点新闻。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            logger.info(f"正在调用 Deepseek API，尝试次数: {retry_count + 1}/{max_retries}")
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 提取回复内容
            json_response = result["choices"][0]["message"]["content"]
            
            # 提取JSON部分
            json_str = json_response
            if "```json" in json_response:
                json_str = json_response.split("```json")[1].split("```")[0].strip()
            
            # 保存Deepseek的输出结果，使用相对路径
            output_directory = os.path.join("data", "outputs")
            os.makedirs(output_directory, exist_ok=True)
            output_filename = os.path.join(output_directory, f"deepseek_output_{today}_{timestamp}.json")
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"已保存Deepseek输出数据至 {output_filename}")
            
            

            # 保存Deepseek的完整响应结果
            output_directory = os.path.join("data", "outputs")
            os.makedirs(output_directory, exist_ok=True)
            
            # 保存原始响应
            raw_output_filename = os.path.join(output_directory, f"deepseek_raw_response_{today}_{timestamp}.json")
            with open(raw_output_filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存Deepseek原始响应至 {raw_output_filename}")
            
            # 保存处理后的JSON输出
            output_filename = os.path.join(output_directory, f"deepseek_output_{today}_{timestamp}.json")
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"已保存Deepseek输出数据至 {output_filename}")
            
            # 解析JSON
            try:
                news_items = json.loads(json_str)
                
                # 根据JSON构建最终输出
                formatted_summary = ""
                for index, news in enumerate(news_items[:20]):
                    num = str(index + 1).zfill(2)
                    title = news.get("title", "未知标题")
                    
                    formatted_summary += f"## ** {num} {title} **  \n"
                    
                    # 添加相关链接，使用优化的格式
                    related_ids = news.get("related_ids", [])
                    for news_id in related_ids:
                        if news_id in hotspot_dict:
                            item = hotspot_dict[news_id]
                            source_name = SOURCE_NAME_MAP.get(item['source'], item['source'])
                            item_title = item['title']
                            # 格式化标题，确保长度一致
                            if len(item_title) > 18:
                                item_title = item_title[:15] + "..."
                            
                            # 添加链接
                            formatted_summary += f"- [{item_title}]({item['url']}) `🏷️{source_name}`\n"
                    
                    # 添加空行分隔
                    formatted_summary += "\n"
                
                # 保存格式化后的摘要内容
                summary_filename = os.path.join(output_directory, f"formatted_summary_{today}_{timestamp}.md")
                with open(summary_filename, 'w', encoding='utf-8') as f:
                    f.write(formatted_summary)
                logger.info(f"已保存格式化摘要至 {summary_filename}")
                
                return formatted_summary
                
            except json.JSONDecodeError as e:
                logger.error(f"解析Deepseek返回的JSON失败: {str(e)}")
                return f"解析Deepseek返回的JSON失败: {str(e)}"
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {e}")
                logger.error(f"原始JSON字符串: {json_str}")
                raise
            
        except requests.exceptions.Timeout:
            retry_count += 1
            logger.warning(f"Deepseek API 请求超时，正在重试 ({retry_count}/{max_retries})...")
            time.sleep(5)  # 等待5秒后重试
        
        except Exception as e:
            logger.error(f"调用Deepseek API时发生错误: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"5秒后重试 ({retry_count}/{max_retries})...")
                time.sleep(5)
            else:
                break
    
    # 如果所有重试都失败，返回前20条热点作为备选
    logger.warning("无法使用Deepseek API归类热点，将使用原始热点")
    fallback = ""
    for i, item in enumerate(hotspots[:10]):
        num = str(i + 1).zfill(2)
        source_name = SOURCE_NAME_MAP.get(item['source'], item['source'])
        item_title = item['title']
        # 格式化标题，确保长度一致
        formatted_title = format_title_for_display(item_title, source_name, 30)
        fallback += f"## ** {num} {item['title']} **  \n"
        fallback += f"- [{item_title}]({item['url']}) `🏷️{source_name}` \n\n"
    return fallback



def send_to_webhook(webhook_url, content, is_tech_only=False):
    """
    将内容发送到webhook·
    保存发送的内容到文件
    """
    try:
        # 获取当前日期和时间
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        
        # 根据是否只包含科技热点来设置标题
        title_prefix = "科技热点" if is_tech_only else "热点新闻"
        
        # 添加标题和查看全部热点的链接
        header = f"# {today} {current_time} {title_prefix}早报\n\n"
        footer = f"\n\n[查看全部热点](https://hot.tuber.cc/)"
        
        # 构建企业微信markdown格式的内容
        markdown_content = header + content + footer
        
        # 保存发送到webhook的内容
        output_directory = os.path.join("data", "webhook")
        os.makedirs(output_directory, exist_ok=True)
        timestamp = now.strftime("%H-%M-%S")
        webhook_filename = os.path.join(output_directory, f"webhook_content_{today}_{timestamp}.md")
        with open(webhook_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        logger.info(f"已保存webhook发送内容至 {webhook_filename}")
        
        # 企业微信webhook格式
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content
            }
        }
        
        # 保存完整的webhook请求
        webhook_request_filename = os.path.join(output_directory, f"webhook_request_{today}_{timestamp}.json")
        with open(webhook_request_filename, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存webhook请求数据至 {webhook_request_filename}")
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        # 保存webhook响应
        webhook_response_filename = os.path.join(output_directory, f"webhook_response_{today}_{timestamp}.json")
        try:
            response_data = response.json()
            with open(webhook_response_filename, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)
        except:
            with open(webhook_response_filename, 'w', encoding='utf-8') as f:
                f.write(f"Status Code: {response.status_code}\nContent: {response.text}")
        logger.info(f"已保存webhook响应至 {webhook_response_filename}")
        
        logger.info(f"成功推送{title_prefix}到webhook")
        return True
    except Exception as e:
        logger.error(f"推送到webhook时发生错误: {str(e)}")
        return False


def filter_recent_hotspots(hotspots, days=1):
    """
    筛选时间范围内的热点数据
    时间范围：昨天整天 + 今天到当前时间
    """
    filtered_hotspots = []
    current_time = datetime.now()
    
    # 设置时间范围：昨天0点到现在
    yesterday = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    
    logger.info(f"当前时间: {current_time}, 筛选时间范围: {yesterday} 至 {current_time}")
    
    for item in hotspots:
        # 尝试解析时间戳
        timestamp = item.get("timestamp") or item.get("time", "")
        
        if timestamp:
            try:
                # 将时间戳转换为datetime对象
                if isinstance(timestamp, str):
                    if 'T' in timestamp and ('Z' in timestamp or '+' in timestamp):
                        # ISO格式: 2025-03-08T12:04:22.020Z
                        item_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        # 尝试作为数字处理
                        timestamp = float(timestamp)
                        # 毫秒级时间戳转换为秒级时间戳
                        if timestamp > 9999999999:
                            timestamp = timestamp / 1000
                        item_time = datetime.fromtimestamp(timestamp)
                else:
                    # 数字类型时间戳
                    if timestamp > 9999999999:  # 毫秒级时间戳
                        timestamp = timestamp / 1000
                    item_time = datetime.fromtimestamp(float(timestamp))
                
                # 检查时间是否在未来（可能是错误的时间戳）
                if item_time > current_time + timedelta(hours=1):
                    # 可能是未来的时间戳，尝试调整年份
                    logger.warning(f"检测到未来时间戳: {item_time}, 标题: {item['title']}")
                    
                    # 如果时间戳对应的年份是未来年份，调整为当前年份
                    if item_time.year > current_time.year:
                        adjusted_year = current_time.year
                        try:
                            item_time = item_time.replace(year=adjusted_year)
                            logger.info(f"调整时间戳年份为当前年份: {item_time}")
                        except ValueError as e:
                            logger.warning(f"调整时间戳年份失败: {str(e)}")
                
                # 记录解析结果
                logger.info(f"热点: {item['title'][:30]}..., 时间: {item_time}")
                
                # 只保留昨天0点到现在的热点
                if yesterday <= item_time <= current_time:
                    filtered_hotspots.append(item)
                    continue
                else:
                    logger.info(f"丢弃时间范围外热点: {item['title']}, 时间: {item_time}")
                    continue
            except (ValueError, TypeError) as e:
                logger.warning(f"解析时间戳失败: {timestamp}, 错误: {str(e)}, 标题: {item['title']}")
        
        # 如果没有有效的时间戳或解析失败，默认保留该条目
        logger.info(f"无有效时间戳，默认保留: {item['title']}")
        filtered_hotspots.append(item)
    
    logger.info(f"筛选后保留 {len(filtered_hotspots)}/{len(hotspots)} 条时间范围内的热点数据")
    return filtered_hotspots
def fetch_rss_articles(rss_url, days=1):
    """
    从RSS源获取最近指定天数内的文章
    """
    try:
        logger.info(f"正在获取RSS源: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        if feed.bozo:  # 检查feed解析是否有错误
            logger.warning(f"RSS解析警告: {feed.bozo_exception}")
        
        articles = []
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(days=days)
        
        for entry in feed.entries:
            # 尝试获取发布时间
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_time = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            else:
                # 如果没有时间信息，假设是最近的
                pub_time = current_time
            
            # 获取作者信息作为来源
            source = "公众号精选"
            if hasattr(entry, 'author') and entry.author:
                source = f"{entry.author}"
            
            # 只保留最近days天的文章
            if pub_time >= cutoff_time:
                articles.append({
                    "title": entry.title,
                    "url": entry.link,
                    "source": source,
                    "hot": "",
                    "published": pub_time.strftime("%Y-%m-%d %H:%M:%S")
                })
        
        logger.info(f"从RSS源获取到 {len(articles)} 篇最近{days}天的文章")
        return articles
    except Exception as e:
        logger.error(f"获取RSS源时发生错误: {str(e)}")
        return []
def main():
    parser = argparse.ArgumentParser(description="热点新闻收集与推送工具")
    parser.add_argument("--tech-only", action="store_true", help="仅收集科技相关的热点")
    parser.add_argument("--webhook", required=True, help="Webhook URL")
    parser.add_argument("--deepseek-key", required=True, help="Deepseek API Key")
    parser.add_argument("--hunyuan-key", required=True, help="腾讯混元 API Key")
    parser.add_argument("--no-cache", action="store_true", 
                        help="禁用摘要缓存，强制重新生成所有摘要")
    parser.add_argument("--base-url", default="https://api-hot.tuber.cc", help="DailyHotApi 基础URL")
    parser.add_argument("--deepseek-url", default="https://ark.cn-beijing.volces.com/api/v3/chat/completions", 
                        help="Deepseek API URL")
    parser.add_argument("--model-id", default="ep-20250307234946-b2znq", 
                        help="Deepseek Model ID")
    parser.add_argument("--rss-url", default="https://wewe.tuber.cc/feeds/all.atom?limit=20", 
                        help="RSS源URL")
    parser.add_argument("--rss-days", type=int, default=1, 
                        help="获取RSS中最近几天的文章")
    parser.add_argument("--title-length", type=int, default=20, 
                        help="显示标题的最大长度")
    parser.add_argument("--max-workers", type=int, default=5, 
                        help="并发处理网页内容的最大线程数")
    parser.add_argument("--skip-content", action="store_true", 
                        help="跳过获取网页内容和生成摘要步骤")
    parser.add_argument("--filter-days", type=int, default=1,
                        help="筛选最近几天的热点数据")
    args = parser.parse_args()
    
    # 检查 BASE_URL 是否可访问
    if not check_base_url(args.base_url):
        logger.error(f"BASE_URL {args.base_url} 不可访问，程序退出")
        sys.exit(1)
    
    # 根据参数选择信息源
    sources = TECH_SOURCES if args.tech_only else ALL_SOURCES
    
    # 收集热点
    hotspots = collect_all_hotspots(sources, args.base_url)
    
    if not hotspots:
        logger.error("未收集到任何热点数据，程序退出")
        sys.exit(1)
    
    # 保存原始热点数据
    save_hotspots_to_jsonl(hotspots)
    
    # 筛选最近的热点
    hotspots = filter_recent_hotspots(hotspots, args.filter_days)
    
    # 保存筛选后的热点数据
    save_hotspots_to_jsonl(hotspots, directory=os.path.join("data", "filtered"))
    
    # 获取RSS文章
    rss_articles = fetch_rss_articles(args.rss_url, args.rss_days)
    
    # 合并热点和RSS文章
    all_content = hotspots + rss_articles
    logger.info(f"合并后共有 {len(all_content)} 条内容")
    
    # 保存合并后的数据
    save_hotspots_to_jsonl(all_content, directory=os.path.join("data", "merged"))
    
    # 获取网页内容并生成摘要
    if not args.skip_content:
        try:
            # 确保有事件循环
            if asyncio.get_event_loop().is_closed():
                asyncio.set_event_loop(asyncio.new_event_loop())
            
            # 使用异步方式处理所有内容，传递tech_only参数和use_cache参数
            loop = asyncio.get_event_loop()
            all_content_with_summary = loop.run_until_complete(
                process_hotspot_with_summary(all_content, args.hunyuan_key, args.max_workers, 
                                           args.tech_only, use_cache=not args.no_cache)
            )
            logger.info(f"已为 {len(all_content_with_summary)} 条内容生成摘要")
        except Exception as e:
            logger.error(f"获取网页内容或生成摘要时发生错误: {str(e)}")
            # 如果出错，继续使用原始内容
            all_content_with_summary = all_content
    else:
        all_content_with_summary = all_content
        logger.info("已跳过获取网页内容和生成摘要步骤")
    
    # 使用Deepseek汇总，传递tech_only参数
    summary = summarize_with_deepseek(all_content_with_summary, args.deepseek_key, 
                                     args.deepseek_url, args.model_id, tech_only=args.tech_only)
    
    # 发送到webhook
    send_to_webhook(args.webhook, summary, args.tech_only)
    
    logger.info("处理完成")

if __name__ == "__main__":
    main()
