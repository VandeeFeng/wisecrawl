#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新的RSS解析器
"""

import os
import sys
import logging
import feedparser
import requests
from datetime import datetime
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

# 导入配置和解析器
from config.config import RSS_FEEDS
from crawler.rss_parser import extract_rss_entry

def test_rss_parser(feed_info):
    """
    测试RSS解析器对特定RSS源的处理效果
    
    参数:
        feed_info: 包含name和url的字典
    """
    feed_name = feed_info.get('name', '未知来源')
    feed_url = feed_info.get('url')
    
    if not feed_url:
        logger.error(f"RSS源 {feed_name} 未提供URL")
        return
    
    try:
        # 设置请求头，模拟浏览器行为
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 获取RSS内容
        logger.info(f"获取RSS源: {feed_name} ({feed_url})")
        response = requests.get(feed_url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        # 打印原始RSS响应内容（前1000个字符）
        logger.info(f"原始RSS响应内容（前1000个字符）:\n{response.content.decode('utf-8', errors='ignore')[:1000]}...")
        
        # 解析RSS
        feed = feedparser.parse(response.content)
        
        # 检查是否有解析错误
        if hasattr(feed, 'bozo') and feed.bozo:
            logger.warning(f"RSS源 {feed_name} 解析警告: {feed.bozo_exception}")
        
        # 检查是否有条目
        if not hasattr(feed, 'entries') or len(feed.entries) == 0:
            logger.error(f"RSS源 {feed_name} 没有条目")
            return
        
        # 检测是否为Atom格式
        is_atom_format = False
        if hasattr(feed, 'namespaces') and 'http://www.w3.org/2005/Atom' in feed.namespaces.values():
            is_atom_format = True
            logger.info(f"检测到Atom格式的RSS源: {feed_name}")
        
        # 测试前3个条目（如果有）
        entries_to_show = min(3, len(feed.entries))
        logger.info(f"RSS源 {feed_name} 共有 {len(feed.entries)} 个条目，测试前 {entries_to_show} 个:")
        
        for i in range(entries_to_show):
            entry = feed.entries[i]
            
            # 打印原始条目结构
            logger.info(f"\n原始条目 {i+1} 结构:")
            for key in entry.keys():
                value = getattr(entry, key)
                value_preview = str(value)[:100] + '...' if len(str(value)) > 100 else str(value)
                logger.info(f"字段: {key}, 值: {value_preview}")
            
            # 使用新的解析器提取信息
            entry_data = extract_rss_entry(entry)
            
            logger.info(f"\n条目 {i+1}: {entry_data['title']}")
            logger.info(f"链接: {entry_data['link']}")
            logger.info(f"作者: {entry_data['author']}")
            logger.info(f"发布时间: {entry_data['published']}")
            
            # 检查内容
            if entry_data['content']:
                content_preview = entry_data['content'][:100] + '...' if len(entry_data['content']) > 100 else entry_data['content']
                logger.info(f"内容: {content_preview}")
                logger.info(f"内容长度: {len(entry_data['content'])}")
            else:
                logger.info("内容: 无")
            
            # 检查摘要
            if entry_data['summary']:
                summary_preview = entry_data['summary'][:100] + '...' if len(entry_data['summary']) > 100 else entry_data['summary']
                logger.info(f"摘要: {summary_preview}")
                logger.info(f"摘要长度: {len(entry_data['summary'])}")
            else:
                logger.info("摘要: 无")
    
    except Exception as e:
        logger.error(f"测试RSS源 {feed_name} 时发生错误: {str(e)}")

def main():
    """
    主函数
    """
    # 测试机器之心RSS源
    jiqizhixin_feed = None
    for feed in RSS_FEEDS:
        if feed.get('name') == '机器之心':
            jiqizhixin_feed = feed
            break
    
    if jiqizhixin_feed:
        logger.info("\n测试机器之心RSS源解析\n" + "=" * 50)
        test_rss_parser(jiqizhixin_feed)
    else:
        logger.error("未找到机器之心RSS源配置")
    
    # 可选：测试其他RSS源
    # for feed in RSS_FEEDS[:2]:  # 只测试前两个源
    #     logger.info(f"\n测试RSS源: {feed.get('name')}\n" + "=" * 50)
    #     test_rss_parser(feed)

if __name__ == "__main__":
    main()