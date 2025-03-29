#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
完整数据收集测试脚本
模拟hot_news_daily_push的完整数据收集流程，包括：
1. 从热点API获取热点数据
2. 从RSS源获取文章
3. 合并数据
4. 处理内容（可选爬取网页）
5. 输出收集到的所有新闻资讯到data目录

注意：此脚本不执行推送操作，仅收集数据
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

logger = logging.getLogger(__name__)

# 导入配置
from config.config import (
    TECH_SOURCES, ALL_SOURCES, WEBHOOK_URL, DEEPSEEK_API_KEY, 
    HUNYUAN_API_KEY, BASE_URL, DEEPSEEK_API_URL, DEEPSEEK_MODEL_ID,
    RSS_URL, RSS_DAYS, TITLE_LENGTH, MAX_WORKERS, FILTER_DAYS, RSS_FEEDS
)

# 导入工具函数
from utils.utils import save_hotspots_to_jsonl, check_base_url

# 导入数据收集模块
from crawler.data_collector import collect_all_hotspots, fetch_rss_articles, filter_recent_hotspots

# 导入处理模块
from processor.news_processor import process_hotspot_with_summary

# 导入LLM集成模块
from llm_integration.deepseek_integration import summarize_with_deepseek


async def test_full_data_collection():
    """
    测试完整的数据收集流程，模拟hot_news_main.py的行为，但不执行推送操作
    """
    # 从环境变量中读取配置，优先使用环境变量，如果不存在则使用config.py中的默认值
    tech_only = os.getenv('TECH_ONLY', 'False').lower() in ('true', '1', 't')
    deepseek_key = os.getenv('DEEPSEEK_API_KEY', DEEPSEEK_API_KEY)
    hunyuan_key = os.getenv('HUNYUAN_API_KEY', HUNYUAN_API_KEY)
    no_cache = os.getenv('NO_CACHE', 'False').lower() in ('true', '1', 't')
    base_url = os.getenv('BASE_URL', BASE_URL)
    deepseek_url = os.getenv('DEEPSEEK_API_URL', DEEPSEEK_API_URL)
    model_id = os.getenv('DEEPSEEK_MODEL_ID', DEEPSEEK_MODEL_ID)
    rss_url = os.getenv('RSS_URL', RSS_URL)
    rss_days = int(os.getenv('RSS_DAYS', str(RSS_DAYS)))
    max_workers = int(os.getenv('MAX_WORKERS', str(MAX_WORKERS)))
    skip_content = os.getenv('SKIP_CONTENT', 'False').lower() in ('true', '1', 't')
    filter_days = int(os.getenv('FILTER_DAYS', str(FILTER_DAYS)))
    
    # 检查必要的API密钥是否存在
    if not deepseek_key and not skip_content:
        logger.warning("未提供Deepseek API Key，将跳过使用Deepseek进行汇总")
    
    if not hunyuan_key and not skip_content:
        logger.warning("未提供腾讯混元 API Key，将跳过内容处理")
        skip_content = True
    
    # 检查 BASE_URL 是否可访问
    if not check_base_url(base_url):
        logger.error(f"BASE_URL {base_url} 不可访问，程序退出")
        return
    
    # 根据参数选择信息源
    sources = TECH_SOURCES if tech_only else ALL_SOURCES
    logger.info(f"使用信息源: {'科技相关' if tech_only else '全部'}, 共 {len(sources)} 个源")
    
    # 收集热点
    logger.info("开始收集热点数据...")
    hotspots = collect_all_hotspots(sources, base_url)
    
    if not hotspots:
        logger.error("未收集到任何热点数据，程序退出")
        return
    
    logger.info(f"成功收集到 {len(hotspots)} 条热点数据")
    
    # 保存原始热点数据
    original_file = save_hotspots_to_jsonl(hotspots)
    logger.info(f"原始热点数据已保存到: {original_file}")
    
    # 筛选最近的热点
    hotspots = filter_recent_hotspots(hotspots, filter_days)
    logger.info(f"筛选后剩余 {len(hotspots)} 条热点数据")
    
    # 保存筛选后的热点数据
    filtered_file = save_hotspots_to_jsonl(hotspots, directory=os.path.join("data", "filtered"))
    logger.info(f"筛选后的热点数据已保存到: {filtered_file}")
    
    # 获取RSS文章
    logger.info("开始获取RSS文章...")
    # 优先使用RSS_FEEDS列表，如果为空则使用单个RSS_URL
    rss_articles = fetch_rss_articles(rss_url=rss_url, days=rss_days, rss_feeds=RSS_FEEDS)
    logger.info(f"成功获取到 {len(rss_articles)} 篇RSS文章")
    
    # 合并热点和RSS文章
    all_content = hotspots + rss_articles
    logger.info(f"合并后共有 {len(all_content)} 条内容")
    
    # 保存合并后的数据
    merged_file = save_hotspots_to_jsonl(all_content, directory=os.path.join("data", "merged"))
    logger.info(f"合并后的数据已保存到: {merged_file}")
    
    # 获取网页内容并生成摘要
    if not skip_content:
        try:
            logger.info("开始获取网页内容并生成摘要...")
            # 使用异步方式处理所有内容，传递tech_only参数和use_cache参数
            all_content_with_summary = await process_hotspot_with_summary(
                all_content, hunyuan_key, max_workers, tech_only, use_cache=not no_cache
            )
            logger.info(f"已为 {len(all_content_with_summary)} 条内容生成摘要")
            
            # 保存处理后的数据
            processed_file = save_hotspots_to_jsonl(all_content_with_summary, directory=os.path.join("data", "processed"))
            logger.info(f"处理后的数据已保存到: {processed_file}")
            
            # 使用Deepseek汇总，传递tech_only参数
            if deepseek_key:
                logger.info("开始使用Deepseek汇总内容...")
                summary = summarize_with_deepseek(all_content_with_summary, deepseek_key, 
                                                deepseek_url, model_id, tech_only=tech_only)
                
                # 保存汇总结果
                summary_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "summary")
                os.makedirs(summary_dir, exist_ok=True)
                summary_file = os.path.join(summary_dir, f"summary_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md")
                
                try:
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        f.write(summary)
                    logger.info(f"汇总结果已保存到: {summary_file}")
                except Exception as e:
                    logger.error(f"保存汇总结果时发生错误: {str(e)}")
            else:
                logger.warning("未提供Deepseek API Key，跳过汇总步骤")
        except Exception as e:
            logger.error(f"获取网页内容或生成摘要时发生错误: {str(e)}")
            # 如果出错，继续使用原始内容
            all_content_with_summary = all_content
    else:
        logger.info("已跳过获取网页内容和生成摘要步骤")
    
    logger.info("数据收集测试完成")
    return merged_file


def print_data_sample(file_path, num_samples=3):
    """
    打印数据样本
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return
            
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if not lines:
            logger.warning(f"文件为空: {file_path}")
            return
            
        samples = min(num_samples, len(lines))
        logger.info(f"\n数据样本 (显示前 {samples} 条):")
        
        for i in range(samples):
            try:
                item = json.loads(lines[i])
                logger.info(f"\n样本 {i+1}:")
                logger.info(f"标题: {item.get('title', '无标题')}")
                logger.info(f"来源: {item.get('source', '未知来源')}")
                logger.info(f"URL: {item.get('url', '无URL')}")
                
                # 打印摘要（如果有）
                summary = item.get('summary', item.get('desc', ''))
                if summary:
                    logger.info(f"摘要: {summary[:100]}{'...' if len(summary) > 100 else ''}")
                
                # 打印时间信息（如果有）
                if 'time' in item:
                    logger.info(f"时间: {item['time']}")
                elif 'published' in item:
                    logger.info(f"发布时间: {item['published']}")
            except json.JSONDecodeError:
                logger.warning(f"无法解析JSON: {lines[i][:50]}...")
            except Exception as e:
                logger.warning(f"处理样本 {i+1} 时出错: {str(e)}")
    except Exception as e:
        logger.error(f"打印数据样本时发生错误: {str(e)}")


if __name__ == "__main__":
    try:
        # 确保有事件循环
        if asyncio.get_event_loop().is_closed():
            asyncio.set_event_loop(asyncio.new_event_loop())
        
        # 运行测试
        loop = asyncio.get_event_loop()
        result_file = loop.run_until_complete(test_full_data_collection())
        
        # 打印数据样本
        if result_file:
            print_data_sample(result_file)
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")