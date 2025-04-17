#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试各个RSS源的可访问性和解析情况
"""

import os
import sys
import logging
import feedparser
import requests
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 导入配置
from config.config import RSS_FEEDS

def test_single_rss_feed(feed_info):
    """
    测试单个RSS源的可访问性和解析情况
    
    参数:
        feed_info: 包含name和url的字典，或者包含accounts数组的字典
    
    返回:
        成功解析的条目数量，如果失败则返回-1
    """
    feed_name = feed_info.get('name', '未知来源')
    
    # 处理多账号RSS源
    if 'accounts' in feed_info:
        total_entries = 0
        for account in feed_info['accounts']:
            account_name = account.get('name', '未知账号')
            logger.info(f"测试Twitter账号: {account_name}")
            entries = test_single_rss_feed(account)
            if entries > 0:
                total_entries += entries
        return total_entries if total_entries > 0 else -1
        
    feed_url = feed_info.get('url')
    
    if not feed_url:
        logger.error(f"RSS源 {feed_name} 未提供URL")
        return -1
    
    try:
        # 首先测试URL是否可访问
        logger.info(f"测试RSS源URL可访问性: {feed_name} ({feed_url})")
        # 设置请求头，模拟浏览器行为，避免被网站拦截
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        # 增加重试机制和请求间隔
        max_retries = 3
        retry_delay = 5  # 5秒间隔
        
        for attempt in range(max_retries):
            try:
                response = requests.get(feed_url, headers=headers, timeout=15, allow_redirects=True)
                response.raise_for_status()
                logger.info(f"RSS源URL可访问: {feed_name}, 状态码: {response.status_code}, 内容长度: {len(response.content)} 字节")
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    logger.warning(f"RSS源 {feed_name} 请求被限制 (429), 将在 {retry_delay} 秒后重试 (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                raise
        
        
        # 然后测试是否可以解析为RSS
        logger.info(f"测试RSS源解析: {feed_name}")
        feed = feedparser.parse(response.content)
        
        # 检查是否有解析错误
        if hasattr(feed, 'bozo') and feed.bozo:
            logger.warning(f"RSS源 {feed_name} 解析警告: {feed.bozo_exception}")
        
        # 检查是否有条目
        if not hasattr(feed, 'entries') or len(feed.entries) == 0:
            logger.error(f"RSS源 {feed_name} 没有条目")
            return 0
        
        # 检测是否为Atom格式
        is_atom_format = False
        if hasattr(feed, 'namespaces') and 'http://www.w3.org/2005/Atom' in feed.namespaces.values():
            is_atom_format = True
            logger.info(f"检测到Atom格式的RSS源: {feed_name}")
        
        # 打印前3个条目的信息（如果有）
        entries_to_show = min(3, len(feed.entries))
        logger.info(f"RSS源 {feed_name} 共有 {len(feed.entries)} 个条目，显示前 {entries_to_show} 个:")
        
        for i in range(entries_to_show):
            entry = feed.entries[i]
            title = entry.title
            # 处理可能的CDATA标签
            if isinstance(title, str) and title.startswith('<![CDATA[') and title.endswith(']]>'):
                title = title[9:-3]  # 去除CDATA标签
            
            # 获取发布时间
            pub_time = "未知时间"
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed)).strftime("%Y-%m-%d %H:%M:%S")
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_time = datetime.fromtimestamp(time.mktime(entry.updated_parsed)).strftime("%Y-%m-%d %H:%M:%S")
            
            # 获取作者信息
            author = "未知作者"
            if hasattr(entry, 'author'):
                if isinstance(entry.author, dict) and 'name' in entry.author:
                    author = entry.author.name
                else:
                    author = str(entry.author)
            
            # 检查是否有内容
            has_content = False
            content_length = 0
            if hasattr(entry, 'content') and entry.content:
                has_content = True
                # 打印content字段的原始结构，帮助调试
                logger.info(f"    Content原始结构: {type(entry.content)}, 值: {entry.content}")
                if isinstance(entry.content, list) and len(entry.content) > 0:
                    content_item = entry.content[0]
                    logger.info(f"    Content第一项类型: {type(content_item)}, 值: {content_item}")
                    if isinstance(content_item, dict) and 'value' in content_item:
                        content_length = len(content_item.value)
                        logger.info(f"    Content值类型: {type(content_item.value)}")
                    elif hasattr(content_item, 'value'):
                        content_length = len(content_item.value)
                        logger.info(f"    Content值类型: {type(content_item.value)}")
            
            # 检查是否有摘要
            has_summary = False
            summary_length = 0
            if hasattr(entry, 'summary') and entry.summary:
                has_summary = True
                if isinstance(entry.summary, dict) and 'value' in entry.summary:
                    summary_length = len(entry.summary.value)
                else:
                    summary_length = len(entry.summary)
            
            logger.info(f"  条目 {i+1}: {title}")
            logger.info(f"    链接: {entry.link}")
            logger.info(f"    作者: {author}")
            logger.info(f"    发布时间: {pub_time}")
            logger.info(f"    有内容: {has_content}, 内容长度: {content_length}")
            logger.info(f"    有摘要: {has_summary}, 摘要长度: {summary_length}")
        
        return len(feed.entries)
    except requests.exceptions.RequestException as e:
        logger.error(f"RSS源 {feed_name} URL访问失败: {str(e)}")
        return -1
    except Exception as e:
        logger.error(f"测试RSS源 {feed_name} 时发生错误: {str(e)}")
        return -1

def test_all_rss_feeds():
    """
    测试所有配置的RSS源
    """
    if not RSS_FEEDS or not isinstance(RSS_FEEDS, list) or len(RSS_FEEDS) == 0:
        logger.error("未配置任何RSS源")
        return
    
    logger.info(f"开始测试 {len(RSS_FEEDS)} 个RSS源")
    
    results = []
    for feed_info in RSS_FEEDS:
        feed_name = feed_info.get('name', '未知来源')
        logger.info(f"\n{'='*50}\n测试RSS源: {feed_name}\n{'='*50}")
        entries_count = test_single_rss_feed(feed_info)
        
        status = "成功" if entries_count >= 0 else "失败"
        results.append({
            "name": feed_name,
            "url": feed_info.get('url', ''),
            "status": status,
            "entries_count": entries_count if entries_count >= 0 else 0
        })
    
    # 打印测试结果摘要
    logger.info("\n\n测试结果摘要:")
    logger.info(f"{'='*70}")
    logger.info(f"{'RSS源名称':<20} | {'状态':<10} | {'条目数':<10} | {'URL':<30}")
    logger.info(f"{'-'*70}")
    
    for result in results:
        logger.info(f"{result['name']:<20} | {result['status']:<10} | {result['entries_count']:<10} | {result['url'][:30]}")
    
    # 统计成功和失败的数量
    success_count = sum(1 for r in results if r['status'] == '成功')
    fail_count = sum(1 for r in results if r['status'] == '失败')
    
    logger.info(f"{'='*70}")
    logger.info(f"总计: {len(results)} 个RSS源, 成功: {success_count}, 失败: {fail_count}")
    return

if __name__ == "__main__":
    test_all_rss_feeds()