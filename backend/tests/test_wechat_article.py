#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试微信公众号文章内容提取
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from crawler.web_crawler import fetch_webpage_content, extract_publish_time_from_html

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

import argparse

def test_article_extraction(url):
    """
    测试网页文章内容提取
    """
    print(f"开始提取文章: {url}")
    
    # 获取文章内容
    content, html = fetch_webpage_content(url, timeout=15, max_retries=3)
    
    # 打印提取结果
    if content:
        print(f"\n成功提取文章内容，长度: {len(content)} 字符")
        print("\n文章内容预览 (前500字符):")
        print("-" * 80)
        print(content[:500] + "...")
        print("-" * 80)
        
        # 尝试提取发布时间
        if html:
            publish_time = extract_publish_time_from_html(html, url)
            if publish_time:
                print(f"\n文章发布时间: {publish_time}")
            else:
                print("\n未能提取到文章发布时间")
    else:
        print("\n未能提取到文章内容")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='测试网页文章内容提取')
    parser.add_argument('url', help='要测试的文章URL')
    args = parser.parse_args()
    test_article_extraction(args.url)