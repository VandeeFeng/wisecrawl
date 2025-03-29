#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试网页内容爬取模块
"""

import sys
import os
import unittest
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from crawler.web_crawler import (
    fetch_webpage_content,
    extract_content_with_multiple_methods,
    extract_publish_time_from_html
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class TestWebCrawler(unittest.TestCase):
    """测试网页内容爬取模块"""
    
    def test_libraries_import(self):
        """测试newspaper3k和trafilatura库是否能正常导入"""
        try:
            import newspaper
            from newspaper import Article
            self.assertTrue(True, "newspaper3k库导入成功")
        except ImportError as e:
            self.fail(f"newspaper3k库导入失败: {str(e)}")
        
        try:
            import trafilatura
            from trafilatura.settings import use_config
            from trafilatura import extract
            self.assertTrue(True, "trafilatura库导入成功")
        except ImportError as e:
            self.fail(f"trafilatura库导入失败: {str(e)}")
    
    def test_extract_content_with_multiple_methods(self):
        """测试多种方法提取网页内容"""
        # 简单的HTML内容用于测试
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试页面</title>
            <meta property="article:published_time" content="2024-05-01T12:00:00+08:00">
        </head>
        <body>
            <article class="content">
                <h1>测试标题</h1>
                <p>这是一段测试内容，用于测试网页内容提取功能。</p>
                <p>这是第二段测试内容。</p>
            </article>
            <div class="footer">版权所有 © 2024</div>
        </body>
        </html>
        """
        
        # 测试内容提取
        url = "https://example.com/test"
        extracted_content = extract_content_with_multiple_methods(html_content, url)
        
        # 验证是否提取到了内容
        self.assertIsNotNone(extracted_content)
        self.assertGreater(len(extracted_content), 0)
        
        # 验证是否包含了文章内容
        self.assertIn("测试标题", extracted_content) or self.assertIn("测试内容", extracted_content)
    
    def test_extract_publish_time(self):
        """测试提取发布时间"""
        # 简单的HTML内容用于测试
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试页面</title>
            <meta property="article:published_time" content="2024-05-01T12:00:00+08:00">
        </head>
        <body>
            <article>
                <h1>测试标题</h1>
                <p>这是测试内容</p>
            </article>
        </body>
        </html>
        """
        
        # 测试时间提取
        url = "https://example.com/test"
        publish_time = extract_publish_time_from_html(html_content, url)
        
        # 验证是否提取到了时间
        self.assertIsNotNone(publish_time)
    
    def test_fetch_webpage_content_with_existing_content(self):
        """测试使用已有内容时的行为"""
        url = "https://example.com/test"
        existing_content = "这是已有的内容，应该直接返回而不进行爬取"
        
        # 测试使用已有内容
        content, html = fetch_webpage_content(url, existing_content=existing_content)
        
        # 验证是否直接返回了已有内容
        self.assertEqual(content, existing_content)
        self.assertEqual(html, "")

if __name__ == "__main__":
    # 检查命令行参数数量
    if len(sys.argv) == 2:
        # 如果提供了URL作为参数
        test_url = sys.argv[1]
        print(f"--- 单独测试 fetch_webpage_content ---")
        print(f"目标 URL: {test_url}")
        try:
            # 直接调用函数进行测试
            # 注意：这里可以调整超时时间和重试次数
            content, html = fetch_webpage_content(test_url, timeout=30, max_retries=2)

            if content:
                print("\n--- 提取到的内容 (前 500 字符) ---")
                print(content[:500] + ("..." if len(content) > 500 else ""))
                print(f"\n--- 内容总长度: {len(content)} 字符 ---")
                # 也可以尝试提取时间
                publish_time = extract_publish_time_from_html(html, test_url)
                if publish_time:
                    print(f"--- 提取到的发布时间: {publish_time} ---")
                else:
                    print("--- 未能提取到发布时间 ---")
            else:
                print("\n--- 未能提取到有效内容 ---")

            # 可以选择性地打印原始HTML的部分内容
            # if html:
            #     print("\n--- 获取到的HTML (前 200 字符) ---")
            #     print(html[:200] + "...")

        except Exception as e:
            print(f"\n--- 测试 fetch_webpage_content 时发生错误 ---")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            # 可以在这里添加更详细的错误追踪信息，如果需要的话
            # import traceback
            # traceback.print_exc()

        # 不再调用 unittest.main()
    else:
        # 如果没有提供额外参数，或者参数数量不为2，则运行标准的单元测试
        print("--- 运行标准单元测试套件 ---")
        # 需要将脚本名从参数中移除，否则unittest会尝试运行它
        unittest.main(argv=[sys.argv[0]])