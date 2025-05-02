#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""测试RSS数据处理流程的脚本
从RSS获取信息，经过爬取处理，到准备送往内容处理模型前的完整流程测试
"""

import os
import sys
import json
import asyncio
import logging
import unittest
from unittest.mock import patch, MagicMock
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

# 导入被测试的模块
from processor.news_processor import process_hotspot_with_summary
from crawler.web_crawler import fetch_webpage_content, extract_publish_time_from_html
from llm_integration.content_integration import summarize_with_content_model


class TestRSSProcessing(unittest.TestCase):
    """测试RSS数据处理流程"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 测试数据 - 模拟RSS条目
        self.test_rss_items = [
            # 已有内容和摘要的RSS条目
            {
                "title": "测试RSS标题1 - 已有内容和摘要",
                "url": "https://example.com/rss1",
                "source": "公众号-测试作者",
                "content": "这是一篇测试文章的完整内容，已经从RSS源中获取。这篇文章包含了足够的信息，不需要再次爬取网页。" * 3,
                "desc": "这是一篇测试文章的摘要，已经从RSS源中获取。",
                "published": "2025-03-12 10:00:00"
            },
            # 已有摘要但无内容的RSS条目
            {
                "title": "测试RSS标题2 - 已有摘要无内容",
                "url": "https://example.com/rss2",
                "source": "公众号-另一位作者",
                "desc": "这是另一篇测试文章的摘要，但没有完整内容。",
                "published": "2025-03-12 11:00:00"
            },
            # 无摘要无内容的RSS条目
            {
                "title": "测试RSS标题3 - 无摘要无内容",
                "url": "https://example.com/rss3",
                "source": "测试技术博客",
                "published": "2025-03-12 12:00:00"
            },
            # 有时间戳的RSS条目
            {
                "title": "测试RSS标题4 - 有时间戳",
                "url": "https://example.com/rss4",
                "source": "测试新闻源",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "published": "2025-03-12 13:00:00"
            }
        ]
        
        # 为每个条目添加saved_at字段，模拟保存时的时间戳
        for item in self.test_rss_items:
            item['saved_at'] = datetime.now().isoformat()
        
        # 模拟的网页内容和HTML
        self.mock_webpage_content = "这是从网页爬取的内容，用于测试。" * 10
        self.mock_html_content = f"<html><body><article><h1>测试标题</h1><div class='content'>{self.mock_webpage_content}</div><div class='time'>2025-03-12 14:00:00</div></article></body></html>"
        
        # 模拟的摘要结果
        self.mock_summary_result = {
            "summary": "这是由内容处理模型生成的测试摘要。",
            "is_tech": True
        }
        
        # 测试用的API密钥
        self.test_api_key = "test_content_model_api_key"
    
    @patch('processor.news_processor.fetch_webpage_content')
    @patch('processor.news_processor.extract_publish_time_from_html')
    @patch('processor.news_processor.summarize_with_content_model')
    @patch('processor.news_processor.os.path.exists')
    @patch('processor.news_processor.open')
    async def test_process_hotspot_with_summary(self, mock_open, mock_exists, mock_summarize, mock_extract_time, mock_fetch):
        """测试process_hotspot_with_summary函数"""
        # 设置模拟函数的返回值
        mock_fetch.return_value = (self.mock_webpage_content, self.mock_html_content)
        mock_extract_time.return_value = datetime.strptime("2025-03-12 14:00:00", "%Y-%m-%d %H:%M:%S")
        mock_summarize.return_value = self.mock_summary_result
        mock_exists.return_value = False  # 假设merged文件不存在，避免文件操作
        
        # 调用被测试的函数
        result = await process_hotspot_with_summary(
            self.test_rss_items,
            self.test_api_key,
            max_workers=2,
            tech_only=False,
            use_cache=False
        )
        
        # 验证结果
        self.assertEqual(len(result), len(self.test_rss_items))
        
        # 检查第一个条目 - 已有内容和摘要
        self.assertEqual(result[0]['title'], self.test_rss_items[0]['title'])
        self.assertEqual(result[0]['summary'], self.test_rss_items[0]['desc'])
        self.assertEqual(result[0]['content'], self.test_rss_items[0]['content'])
        self.assertTrue(result[0]['is_tech'])  # 已有摘要的条目默认设为科技相关
        self.assertTrue(result[0]['is_processed'])
        
        # 检查第二个条目 - 已有摘要无内容
        self.assertEqual(result[1]['title'], self.test_rss_items[1]['title'])
        self.assertEqual(result[1]['summary'], self.test_rss_items[1]['desc'])
        self.assertEqual(result[1]['content'], self.mock_webpage_content)  # 应该爬取了内容
        self.assertTrue(result[1]['is_tech'])
        self.assertTrue(result[1]['is_processed'])
        
        # 检查第三个条目 - 无摘要无内容
        self.assertEqual(result[2]['title'], self.test_rss_items[2]['title'])
        self.assertEqual(result[2]['summary'], self.mock_summary_result['summary'])  # 应该生成了摘要
        self.assertEqual(result[2]['content'], self.mock_webpage_content)  # 应该爬取了内容
        self.assertTrue(result[2]['is_tech'])
        self.assertTrue(result[2]['is_processed'])
        
        # 检查第四个条目 - 有时间戳
        self.assertEqual(result[3]['title'], self.test_rss_items[3]['title'])
        self.assertEqual(result[3]['summary'], self.mock_summary_result['summary'])  # 应该生成了摘要
        self.assertEqual(result[3]['content'], self.mock_webpage_content)  # 应该爬取了内容
        self.assertTrue(result[3]['is_tech'])
        self.assertTrue(result[3]['is_processed'])
        
        # 验证函数调用
        # 第一个条目不应该调用fetch_webpage_content和summarize_with_content_model
        # 第二个条目应该调用fetch_webpage_content但不调用summarize_with_content_model
        # 第三个和第四个条目应该都调用fetch_webpage_content和summarize_with_content_model
        self.assertEqual(mock_fetch.call_count, 3)  # 应该被调用3次（第2、3、4个条目）
        self.assertEqual(mock_summarize.call_count, 2)  # 应该被调用2次（第3、4个条目）
        
    @patch('crawler.web_crawler.requests.get')
    def test_fetch_webpage_content_with_existing_content(self, mock_get):
        """测试fetch_webpage_content函数，当已有内容时应跳过爬取"""
        existing_content = "这是已有的内容，应该直接使用而不进行爬取。" * 5
        
        # 调用函数
        content, html = fetch_webpage_content(
            "https://example.com/test",
            existing_content=existing_content
        )
        
        # 验证结果
        self.assertEqual(content, existing_content)
        self.assertEqual(html, "")  # HTML应为空字符串
        
        # 验证requests.get没有被调用
        mock_get.assert_not_called()
    
    @patch('llm_integration.content_integration.load_summary_cache')
    @patch('llm_integration.content_integration.save_summary_cache')
    @patch('llm_integration.content_integration.ChatOpenAI')
    def test_summarize_with_cache(self, mock_chat_openai, mock_save_cache, mock_load_cache):
        """测试summarize_with_content_model函数的缓存机制"""
        # 设置模拟缓存
        mock_cache = {
            "test_hash": self.mock_summary_result
        }
        mock_load_cache.return_value = mock_cache
        
        # 模拟get_content_hash函数
        with patch('llm_integration.content_integration.get_content_hash', return_value="test_hash"):
            # 调用函数
            result = summarize_with_content_model(
                "测试内容" * 20,
                self.test_api_key,
                use_cache=True
            )
        
        # 验证结果
        self.assertEqual(result, self.mock_summary_result)
        
        # 验证ChatOpenAI没有被调用（应该从缓存获取）
        mock_chat_openai.assert_not_called()
        
        # 验证缓存加载被调用
        mock_load_cache.assert_called_once()
        
        # 验证缓存保存没有被调用（因为使用了缓存）
        mock_save_cache.assert_not_called()


if __name__ == "__main__":
    unittest.main()