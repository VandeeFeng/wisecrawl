#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主文件：调用各个函数，确保逻辑清晰
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from distutils.util import strtobool

# 导入配置
from config.config import (
    TECH_SOURCES, ALL_SOURCES, WEBHOOK_URL, DEEPSEEK_API_KEY, 
    HUNYUAN_API_KEY, BASE_URL, DEEPSEEK_API_URL, DEEPSEEK_MODEL_ID,
    RSS_URL, RSS_DAYS, TITLE_LENGTH, MAX_WORKERS, FILTER_DAYS, RSS_FEEDS
)

# 导入工具函数
from utils.utils import save_hotspots_to_jsonl, check_base_url, cleanup_old_files

# 导入数据收集模块
from crawler.data_collector import (
    collect_all_hotspots, fetch_rss_articles, filter_recent_hotspots,
    fetch_twitter_feed
)

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
        logger.warning("未能收集到任何热点数据，将继续尝试其他来源...")
        hotspots = [] # 确保 hotspots 是列表
    
    # 保存原始热点数据
    if hotspots:
        save_hotspots_to_jsonl(hotspots, directory=os.path.join("data", "raw")) # 指定 raw 目录
    
    # 筛选最近的热点
    hotspots = filter_recent_hotspots(hotspots, filter_days)
    
    # 保存筛选后的热点数据
    if hotspots:
        save_hotspots_to_jsonl(hotspots, directory=os.path.join("data", "filtered"))
    
    # 获取RSS文章
    # 优先使用RSS_FEEDS列表，如果为空则使用单个RSS_URL
    rss_articles = fetch_rss_articles(rss_url=rss_url, days=rss_days, rss_feeds=RSS_FEEDS)
    
    # --- 新增：获取 Twitter Feed ---
    twitter_feed_raw = fetch_twitter_feed(days_to_fetch=2) # 获取最近2天
    
    # 过滤推文，只保留最近1天 (24小时) 的
    recent_tweets = []
    cutoff_time_tweets = datetime.now() - timedelta(days=1)
    if twitter_feed_raw:
        logger.info(f"开始过滤最近24小时的推文 (截止时间: {cutoff_time_tweets})...")
        for tweet in twitter_feed_raw:
            if tweet.get("timestamp"): # 确保有时间戳
                # Ensure timestamp is treated correctly (it's already in milliseconds from fetch_twitter_feed)
                tweet_time_ms = tweet["timestamp"]
                if isinstance(tweet_time_ms, (int, float)):
                   tweet_time = datetime.fromtimestamp(tweet_time_ms / 1000)
                   if tweet_time >= cutoff_time_tweets:
                       recent_tweets.append(tweet)
                   # else: # 可以取消注释以查看被丢弃的推文
                   #     logger.debug(f"丢弃较早的推文: {tweet['title']} @ {tweet_time}")
                else:
                   logger.warning(f"推文时间戳格式不正确: {tweet_time_ms}, 类型: {type(tweet_time_ms)}, 跳过推文: {tweet.get('title')}")

            else:
                 logger.warning(f"推文缺少时间戳，无法过滤: {tweet.get('title')}")
                 # Decide whether to include tweets without timestamps or skip them
                 # For now, we skip them to ensure only recent ones are included
                 # recent_tweets.append(tweet) # Uncomment to include tweets without timestamp

        logger.info(f"筛选后保留 {len(recent_tweets)}/{len(twitter_feed_raw)} 条最近24小时的推文。")
    # --- 结束：获取 Twitter Feed ---
    
    # 合并热点、RSS文章和过滤后的推文
    all_content = hotspots + rss_articles + recent_tweets # 添加 recent_tweets
    logger.info(f"合并后共有 {len(all_content)} 条内容 (包括推文)")
    
    # 检查合并后是否有内容
    if not all_content:
        logger.error("所有来源均未获取到有效内容，程序退出")
        sys.exit(1)
    
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
    
    # --- 新增：基于标题去重，优先保留 RSS 和 Twitter --- 
    logger.info(f"开始基于标题去重 (保留RSS/Twitter优先)，处理前数量: {len(all_content_with_summary)}")
    seen_titles = {}
    preferred_sources = {"RSS", "Twitter"} # 确认这些是 data_collector 中使用的准确来源名称
    
    for item in all_content_with_summary:
        title = item.get("title", "").strip()
        if not title: # 跳过没有标题的条目
            continue
            
        current_source = item.get("source", "")
    
        if title not in seen_titles:
            seen_titles[title] = item
        else:
            existing_item = seen_titles[title]
            existing_source = existing_item.get("source", "")
            
            # 如果当前条目来源是优先来源，且已存在的条目来源不是优先来源，则替换
            if current_source in preferred_sources and existing_source not in preferred_sources:
                logger.debug(f"去重：替换 '{title}' (来自 {existing_source}) 为来自优先源 {current_source}")
                seen_titles[title] = item
            # 如果两者都是优先来源，或都不是，保留先遇到的那个（目前逻辑）
            # 可以根据需要添加更复杂的优先级，例如 RSS 优先于 Twitter
            # else:
            #    logger.debug(f"去重：保留 '{title}' (来自 {existing_source}), 忽略来自 {current_source}")
                
    deduplicated_content = list(seen_titles.values())
    logger.info(f"去重后剩余数量: {len(deduplicated_content)}")
    # --- 结束：去重逻辑 ---

    # --- 新增：保存最终处理和去重后的新闻列表 ---
    logger.info(f"准备保存处理和去重后的 {len(deduplicated_content)} 条新闻...")
    processed_output_dir = os.path.join("data", "processed_output")
    os.makedirs(processed_output_dir, exist_ok=True) # 确保目录存在
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    processed_filename = os.path.join(processed_output_dir, f"processed_news_{timestamp_str}.json")
    
    try:
        # 导入 json 模块（如果尚未导入）
        import json 
        with open(processed_filename, 'w', encoding='utf-8') as f:
            json.dump(deduplicated_content, f, ensure_ascii=False, indent=4)
        logger.info(f"成功将处理后的新闻列表保存到: {processed_filename}")
    except Exception as e:
        logger.error(f"保存处理后的新闻列表到 {processed_filename} 时出错: {str(e)}")
    # --- 结束：保存逻辑 ---
    
    # 使用Deepseek汇总，传递tech_only参数
    summary = summarize_with_deepseek(deduplicated_content, deepseek_key, # 使用去重后的列表
                                     deepseek_url, model_id, tech_only=tech_only)
    
    # 使用多种方式推送消息
    success = notify(summary, tech_only)
    if not success:
        # 如果所有推送方式都失败，尝试使用原始webhook方式作为备选
        logger.warning("所有配置的推送方式均失败，尝试使用原始webhook方式推送")
        send_to_webhook(webhook, summary, tech_only)
    
    logger.info("处理完成")

    # 在这里添加清理逻辑
    # 清理旧数据文件
    directories_to_clean = [
        "data/raw",      # 原始热点数据
        "data/filtered", # 筛选后的热点数据
        "data/merged",   # 合并后的数据
        "data/inputs",   # LLM 输入数据
        "data/outputs",  # LLM 输出数据
        "data/webhook",  # Webhook 日志
        "cache/summary"  # 摘要缓存 (如果需要清理缓存)
    ]
    days_to_keep = 7 # 设置保留天数
    logger.info(f"开始清理超过 {days_to_keep} 天的旧数据...")
    for directory in directories_to_clean:
        cleanup_old_files(directory, days_to_keep=days_to_keep)

    logger.info("旧数据清理完成")

if __name__ == "__main__":
    main()