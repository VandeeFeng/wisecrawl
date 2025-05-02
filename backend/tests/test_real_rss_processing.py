#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
真实RSS数据处理测试脚本
从真实RSS源获取信息，经过爬取处理，到准备送往混元模型前的完整流程测试
"""

import os
import sys
import json
import asyncio
import logging
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

# 导入相关模块
from config.config import RSS_FEEDS, CONTENT_MODEL_API_KEY
from crawler.data_collector import fetch_rss_articles
from processor.news_processor import process_hotspot_with_summary


async def test_real_rss_processing():
    """
    使用真实RSS源测试数据处理流程
    """
    # 检查API密钥是否存在
    content_model_api_key = os.getenv('CONTENT_MODEL_API_KEY', CONTENT_MODEL_API_KEY)
    if not content_model_api_key:
        logging.error("未提供内容处理模型API密钥，请在.env文件中设置CONTENT_MODEL_API_KEY")
        sys.exit(1)
    
    # 获取RSS文章
    logging.info("开始获取RSS文章...")
    rss_articles = fetch_rss_articles(rss_feeds=RSS_FEEDS, days=1)
    
    if not rss_articles:
        logging.error("未获取到任何RSS文章，请检查RSS源配置")
        return
    
    # 记录获取到的RSS文章数量和来源
    sources = {}
    for article in rss_articles:
        source = article.get("source", "未知来源")
        sources[source] = sources.get(source, 0) + 1
    
    logging.info(f"共获取到 {len(rss_articles)} 篇RSS文章，来源分布: {sources}")
    
    # 为每个条目添加saved_at字段，模拟保存时的时间戳
    for item in rss_articles:
        item['saved_at'] = datetime.now().isoformat()
    
    # 选择前5篇文章进行处理，避免处理过多
    test_articles = rss_articles[:5]
    logging.info(f"选择前 {len(test_articles)} 篇文章进行处理测试")
    
    # 打印选择的文章标题
    for i, article in enumerate(test_articles):
        logging.info(f"测试文章 {i+1}: {article['title']} (来源: {article.get('source', '未知')})")
    
    # 处理RSS文章
    logging.info("开始处理RSS文章...")
    processed_articles = await process_hotspot_with_summary(
        test_articles,
        content_model_api_key,
        max_workers=2,  # 使用较少的工作线程
        tech_only=False,
        use_cache=True  # 启用缓存以避免重复处理
    )
    
    # 打印处理结果
    logging.info(f"处理完成，共处理 {len(processed_articles)} 篇文章")
    for i, article in enumerate(processed_articles):
        logging.info(f"\n文章 {i+1}: {article['title']}")
        logging.info(f"来源: {article.get('source', '未知')}")
        logging.info(f"URL: {article.get('url', '未知')}")
        logging.info(f"发布时间: {article.get('published', '未知')}")
        logging.info(f"是否科技相关: {article.get('is_tech', False)}")
        logging.info(f"是否成功处理: {article.get('is_processed', False)}")
        
        # 打印摘要
        summary = article.get('summary', '')
        if summary:
            logging.info(f"摘要: {summary[:100]}{'...' if len(summary) > 100 else ''}")
        else:
            logging.info("摘要: 无")
        
        # 打印内容长度
        content = article.get('content', '')
        if content:
            logging.info(f"内容长度: {len(content)} 字符")
        else:
            logging.info("内容: 无")

    # 处理所有内容
    processed_content = await process_hotspot_with_summary(
        rss_articles, 
        content_model_api_key,
        max_workers=5,
        tech_only=True,
        use_cache=True
    )


async def main():
    """
    主函数
    """
    logging.info("开始执行真实RSS数据处理测试")
    await test_real_rss_processing()
    logging.info("测试完成")


if __name__ == "__main__":
    asyncio.run(main())