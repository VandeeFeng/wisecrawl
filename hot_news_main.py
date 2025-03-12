#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主文件：调用各个函数，确保逻辑清晰
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from distutils.util import strtobool

# 导入配置
from config.config import (
    TECH_SOURCES, ALL_SOURCES, WEBHOOK_URL, DEEPSEEK_API_KEY, 
    HUNYUAN_API_KEY, BASE_URL, DEEPSEEK_API_URL, DEEPSEEK_MODEL_ID,
    RSS_URL, RSS_DAYS, TITLE_LENGTH, MAX_WORKERS, FILTER_DAYS
)

# 导入工具函数
from utils.utils import save_hotspots_to_jsonl, check_base_url

# 导入数据收集模块
from crawler.data_collector import collect_all_hotspots, fetch_rss_articles, filter_recent_hotspots

# 导入处理模块
from processor.news_processor import process_hotspot_with_summary

# 导入LLM集成模块
from llm_integration.deepseek_integration import summarize_with_deepseek

# 导入通知模块
from notification.webhook_sender import notify, send_to_webhook

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # 从环境变量中读取配置，优先使用环境变量，如果不存在则使用config.py中的默认值
    tech_only = bool(strtobool(os.getenv('TECH_ONLY', 'False')))
    webhook = os.getenv('WEBHOOK_URL', WEBHOOK_URL)
    deepseek_key = os.getenv('DEEPSEEK_API_KEY', DEEPSEEK_API_KEY)
    hunyuan_key = os.getenv('HUNYUAN_API_KEY', HUNYUAN_API_KEY)
    no_cache = bool(strtobool(os.getenv('NO_CACHE', 'False')))
    base_url = os.getenv('BASE_URL', BASE_URL)
    deepseek_url = os.getenv('DEEPSEEK_API_URL', DEEPSEEK_API_URL)
    model_id = os.getenv('DEEPSEEK_MODEL_ID', DEEPSEEK_MODEL_ID)
    rss_url = os.getenv('RSS_URL', RSS_URL)
    rss_days = int(os.getenv('RSS_DAYS', str(RSS_DAYS)))
    title_length = int(os.getenv('TITLE_LENGTH', str(TITLE_LENGTH)))
    max_workers = int(os.getenv('MAX_WORKERS', str(MAX_WORKERS)))
    skip_content = bool(strtobool(os.getenv('SKIP_CONTENT', 'False')))
    filter_days = int(os.getenv('FILTER_DAYS', str(FILTER_DAYS)))
    
    # 检查必要的API密钥是否存在
    if not webhook:
        logger.error("未提供Webhook URL，请在环境变量中设置WEBHOOK_URL")
        sys.exit(1)
    
    if not deepseek_key:
        logger.error("未提供Deepseek API Key，请在环境变量中设置DEEPSEEK_API_KEY")
        sys.exit(1)
    
    if not hunyuan_key and not skip_content:
        logger.error("未提供腾讯混元 API Key，请在环境变量中设置HUNYUAN_API_KEY，或设置SKIP_CONTENT=True跳过内容处理")
        sys.exit(1)
    
    # 检查 BASE_URL 是否可访问
    if not check_base_url(base_url):
        logger.error(f"BASE_URL {base_url} 不可访问，程序退出")
        sys.exit(1)
    
    # 根据参数选择信息源
    sources = TECH_SOURCES if tech_only else ALL_SOURCES
    
    # 收集热点
    hotspots = collect_all_hotspots(sources, base_url)
    
    if not hotspots:
        logger.error("未收集到任何热点数据，程序退出")
        sys.exit(1)
    
    # 保存原始热点数据
    save_hotspots_to_jsonl(hotspots)
    
    # 筛选最近的热点
    hotspots = filter_recent_hotspots(hotspots, filter_days)
    
    # 保存筛选后的热点数据
    save_hotspots_to_jsonl(hotspots, directory=os.path.join("data", "filtered"))
    
    # 获取RSS文章
    rss_articles = fetch_rss_articles(rss_url, rss_days)
    
    # 合并热点和RSS文章
    all_content = hotspots + rss_articles
    logger.info(f"合并后共有 {len(all_content)} 条内容")
    
    # 保存合并后的数据
    save_hotspots_to_jsonl(all_content, directory=os.path.join("data", "merged"))
    
    # 获取网页内容并生成摘要
    if not skip_content:
        try:
            # 确保有事件循环
            if asyncio.get_event_loop().is_closed():
                asyncio.set_event_loop(asyncio.new_event_loop())
            
            # 使用异步方式处理所有内容，传递tech_only参数和use_cache参数
            loop = asyncio.get_event_loop()
            all_content_with_summary = loop.run_until_complete(
                process_hotspot_with_summary(all_content, hunyuan_key, max_workers, 
                                           tech_only, use_cache=not no_cache)
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
    summary = summarize_with_deepseek(all_content_with_summary, deepseek_key, 
                                     deepseek_url, model_id, tech_only=tech_only)
    
    # 使用多种方式推送消息
    success = notify(summary, tech_only)
    if not success:
        # 如果所有推送方式都失败，尝试使用原始webhook方式作为备选
        logger.warning("所有配置的推送方式均失败，尝试使用原始webhook方式推送")
        send_to_webhook(webhook, summary, tech_only)
    
    logger.info("处理完成")

if __name__ == "__main__":
    main()