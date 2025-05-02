#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试所有新闻源的完整数据收集流程
包括热点API和RSS源的数据获取、处理和保存
模拟hot_news_main.py的完整调用链路
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
    CONTENT_MODEL_API_KEY, BASE_URL, DEEPSEEK_API_URL, DEEPSEEK_MODEL_ID,
    RSS_URL, RSS_DAYS, TITLE_LENGTH, MAX_WORKERS, FILTER_DAYS, RSS_FEEDS
)

# 导入工具函数
from utils.utils import save_hotspots_to_jsonl, check_base_url

# 导入数据收集模块
from crawler.data_collector import collect_all_hotspots, fetch_rss_articles, filter_recent_hotspots

# 导入处理模块
from processor.news_processor import process_hotspot_with_summary

# 导入测试RSS源的函数
from test_rss_feeds import test_single_rss_feed


def test_single_news_source(source, base_url):
    """
    测试单个热点新闻源的数据获取情况
    
    参数:
        source: 新闻源名称
        base_url: API基础URL
    
    返回:
        获取到的热点数据列表
    """
    logger.info(f"\n{'='*50}\n测试热点新闻源: {source}\n{'='*50}")
    
    try:
        # 从指定源获取热点数据
        hotspots = collect_all_hotspots([source], base_url)
        
        # 打印获取结果
        if hotspots:
            logger.info(f"成功从 {source} 获取到 {len(hotspots)} 条热点数据")
            
            # 打印前3条数据（如果有）
            items_to_show = min(3, len(hotspots))
            logger.info(f"显示前 {items_to_show} 条数据:")
            
            for i in range(items_to_show):
                item = hotspots[i]
                logger.info(f"  数据 {i+1}: {item['title']}")
                logger.info(f"    链接: {item['url']}")
                logger.info(f"    热度: {item.get('hot', '未知')}")
                
                # 打印摘要（如果有）
                if 'desc' in item and item['desc']:
                    desc = item['desc']
                    logger.info(f"    摘要: {desc[:100]}{'...' if len(desc) > 100 else ''}")
            
            # 保存数据到文件
            save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "test_sources")
            os.makedirs(save_dir, exist_ok=True)
            
            filename = os.path.join(save_dir, f"{source}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jsonl")
            with open(filename, 'w', encoding='utf-8') as f:
                for item in hotspots:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            logger.info(f"已将 {source} 的数据保存至 {filename}")
            return hotspots
        else:
            logger.error(f"从 {source} 获取数据失败，未返回任何数据")
            return []
    except Exception as e:
        logger.error(f"测试 {source} 时发生错误: {str(e)}")
        return []


def test_all_rss_sources_with_data_save():
    """
    测试所有RSS源并保存获取到的数据
    """
    if not RSS_FEEDS or not isinstance(RSS_FEEDS, list) or len(RSS_FEEDS) == 0:
        logger.error("未配置任何RSS源")
        return []
    
    logger.info(f"开始测试 {len(RSS_FEEDS)} 个RSS源并保存数据")
    
    all_rss_articles = []
    results = []
    
    # 设置获取最近几天的文章
    days = int(os.getenv('RSS_DAYS', str(RSS_DAYS)))
    
    for feed_info in RSS_FEEDS:
        feed_name = feed_info.get('name', '未知来源')
        feed_url = feed_info.get('url', '')
        
        logger.info(f"\n{'='*50}\n测试RSS源: {feed_name} ({feed_url})\n{'='*50}")
        
        # 先测试RSS源的可访问性和解析情况
        entries_count = test_single_rss_feed(feed_info)
        
        status = "成功" if entries_count >= 0 else "失败"
        results.append({
            "name": feed_name,
            "url": feed_url,
            "status": status,
            "entries_count": entries_count if entries_count >= 0 else 0
        })
        
        # 如果可以访问，则获取文章数据并保存
        if entries_count > 0:
            try:
                # 使用fetch_rss_articles函数获取单个RSS源的文章
                logger.info(f"获取 {feed_name} 的文章数据...")
                articles = fetch_rss_articles(rss_url=feed_url, days=days)
                
                if articles:
                    logger.info(f"成功从 {feed_name} 获取到 {len(articles)} 篇文章")
                    
                    # 为每篇文章添加来源标识
                    for article in articles:
                        if 'source' not in article or not article['source']:
                            article['source'] = feed_name
                    
                    # 添加到总列表
                    all_rss_articles.extend(articles)
                    
                    # 保存到单独的文件
                    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "test_sources", "rss")
                    os.makedirs(save_dir, exist_ok=True)
                    
                    # 生成安全的文件名（去除可能的非法字符）
                    safe_name = "".join([c if c.isalnum() or c in "_- " else "_" for c in feed_name])
                    filename = os.path.join(save_dir, f"{safe_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jsonl")
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        for item in articles:
                            f.write(json.dumps(item, ensure_ascii=False) + '\n')
                    
                    logger.info(f"已将 {feed_name} 的文章数据保存至 {filename}")
                    
                    # 打印前3篇文章（如果有）
                    items_to_show = min(3, len(articles))
                    if items_to_show > 0:
                        logger.info(f"显示前 {items_to_show} 篇文章:")
                        
                        for i in range(items_to_show):
                            article = articles[i]
                            logger.info(f"  文章 {i+1}: {article['title']}")
                            logger.info(f"    链接: {article['url']}")
                            logger.info(f"    来源: {article['source']}")
                            
                            # 打印发布时间（如果有）
                            if 'published' in article:
                                logger.info(f"    发布时间: {article['published']}")
                            
                            # 打印摘要（如果有）
                            if 'desc' in article and article['desc']:
                                desc = article['desc']
                                logger.info(f"    摘要: {desc[:100]}{'...' if len(desc) > 100 else ''}")
                else:
                    logger.warning(f"未从 {feed_name} 获取到任何文章")
            except Exception as e:
                logger.error(f"获取 {feed_name} 的文章数据时发生错误: {str(e)}")
    
    # 保存所有RSS文章到一个合并文件
    if all_rss_articles:
        merged_file = save_hotspots_to_jsonl(all_rss_articles, directory=os.path.join("data", "test_sources"))
        logger.info(f"已将所有RSS文章合并保存到: {merged_file}")
    
    # 打印测试结果摘要
    logger.info("\n\nRSS源测试结果摘要:")
    logger.info(f"{'='*70}")
    logger.info(f"{'RSS源名称':<20} | {'状态':<10} | {'条目数':<10} | {'URL':<30}")
    logger.info(f"{'-'*70}")
    
    for result in results:
        logger.info(f"{result['name']:<20} | {result['status']:<10} | {result['entries_count']:<10} | {result['url'][:30]}")
    
    # 统计成功和失败的数量
    success_count = sum(1 for r in results if r['status'] == '成功')
    fail_count = sum(1 for r in results if r['status'] == '失败')
    
    logger.info(f"{'='*70}")
    logger.info(f"总计: {len(results)} 个RSS源, 成功: {success_count}, 失败: {fail_count}, 获取到 {len(all_rss_articles)} 篇文章")
    
    return all_rss_articles


async def test_all_news_sources():
    """
    测试所有新闻源（包括热点API和RSS源）的完整数据收集流程
    模拟hot_news_main.py的完整调用链路
    """
    # 从环境变量中读取配置，优先使用环境变量，如果不存在则使用config.py中的默认值
    tech_only = os.getenv('TECH_ONLY', 'False').lower() in ('true', '1', 't')
    deepseek_key = os.getenv('DEEPSEEK_API_KEY', DEEPSEEK_API_KEY)
    content_model_key = os.getenv('CONTENT_MODEL_API_KEY', CONTENT_MODEL_API_KEY)
    no_cache = os.getenv('NO_CACHE', 'False').lower() in ('true', '1', 't')
    base_url = os.getenv('BASE_URL', BASE_URL)
    skip_content = os.getenv('SKIP_CONTENT', 'False').lower() in ('true', '1', 't')
    filter_days = int(os.getenv('FILTER_DAYS', str(FILTER_DAYS)))
    max_workers = int(os.getenv('MAX_WORKERS', str(MAX_WORKERS)))
    
    # 检查 BASE_URL 是否可访问
    if not check_base_url(base_url):
        logger.error(f"BASE_URL {base_url} 不可访问，程序退出")
        return
    
    # 根据参数选择信息源
    sources = TECH_SOURCES if tech_only else ALL_SOURCES
    logger.info(f"使用信息源: {'科技相关' if tech_only else '全部'}, 共 {len(sources)} 个源")
    
    # 1. 测试每个热点新闻源
    logger.info("\n\n开始测试每个热点新闻源...")
    all_hotspots = []
    
    for source in sources:
        source_hotspots = test_single_news_source(source, base_url)
        all_hotspots.extend(source_hotspots)
    
    logger.info(f"热点新闻源测试完成，共获取到 {len(all_hotspots)} 条热点数据")
    
    # 保存所有热点数据到一个合并文件
    if all_hotspots:
        merged_hotspots_file = save_hotspots_to_jsonl(all_hotspots, directory=os.path.join("data", "test_sources", "merged"))
        logger.info(f"已将所有热点数据合并保存到: {merged_hotspots_file}")
    
    # 2. 测试所有RSS源
    logger.info("\n\n开始测试所有RSS源...")
    all_rss_articles = test_all_rss_sources_with_data_save()
    logger.info(f"RSS源测试完成，共获取到 {len(all_rss_articles)} 篇RSS文章")
    
    # 3. 合并热点和RSS文章
    all_content = all_hotspots + all_rss_articles
    logger.info(f"\n\n合并后共有 {len(all_content)} 条内容")
    
    # 保存合并后的数据
    if all_content:
        merged_file = save_hotspots_to_jsonl(all_content, directory=os.path.join("data", "test_sources", "all_merged"))
        logger.info(f"已将所有内容合并保存到: {merged_file}")
    
    # 4. 如果提供了API密钥，测试内容处理和摘要生成
    if not skip_content and content_model_key:
        try:
            logger.info("\n\n开始测试内容处理和摘要生成...")
            # 为了避免处理过多内容，只选择部分内容进行处理
            sample_size = min(10, len(all_content))
            sample_content = all_content[:sample_size]
            logger.info(f"选择 {sample_size} 条内容进行处理测试")
            
            # 使用异步方式处理内容
            processed_content = await process_hotspot_with_summary(
                sample_content, content_model_key, max_workers, tech_only, use_cache=not no_cache
            )
            
            logger.info(f"内容处理完成，共处理 {len(processed_content)} 条内容")
            
            # 保存处理后的数据
            if processed_content:
                processed_file = save_hotspots_to_jsonl(processed_content, directory=os.path.join("data", "test_sources", "processed"))
                logger.info(f"已将处理后的内容保存到: {processed_file}")
                
                # 打印处理结果样本
                logger.info("\n处理结果样本:")
                for i in range(min(3, len(processed_content))):
                    item = processed_content[i]
                    logger.info(f"\n样本 {i+1}:")
                    logger.info(f"标题: {item.get('title', '无标题')}")
                    logger.info(f"来源: {item.get('source', '未知来源')}")
                    logger.info(f"是否科技相关: {item.get('is_tech', False)}")
                    logger.info(f"是否成功处理: {item.get('is_processed', False)}")
                    
                    # 打印摘要
                    summary = item.get('summary', '')
                    if summary:
                        logger.info(f"摘要: {summary[:150]}{'...' if len(summary) > 150 else ''}")
        except Exception as e:
            logger.error(f"测试内容处理时发生错误: {str(e)}")
    else:
        logger.info("跳过内容处理测试（未提供API密钥或已设置跳过内容处理）")
    
    logger.info("\n\n所有新闻源测试完成!")
    return all_content


if __name__ == "__main__":
    try:
        # 确保有事件循环
        if asyncio.get_event_loop().is_closed():
            asyncio.set_event_loop(asyncio.new_event_loop())
        
        # 运行测试
        loop = asyncio.get_event_loop()
        all_content = loop.run_until_complete(test_all_news_sources())
        
        # 打印最终结果
        if all_content:
            logger.info(f"\n\n测试完成，共获取到 {len(all_content)} 条内容")
            logger.info(f"其中热点数据: {sum(1 for item in all_content if 'hot' in item and item['hot'])} 条")
            logger.info(f"RSS文章: {sum(1 for item in all_content if 'published' in item)} 条")
            
            # 统计各来源的数量
            sources_count = {}
            for item in all_content:
                source = item.get('source', '未知来源')
                sources_count[source] = sources_count.get(source, 0) + 1
            
            logger.info("\n各来源数据统计:")
            for source, count in sorted(sources_count.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"{source}: {count} 条")
        else:
            logger.warning("测试完成，但未获取到任何内容")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")