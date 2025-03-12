#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻数据收集：收集hotnews和公众号文章
"""

import requests
import logging
import feedparser
import time
import os
from datetime import datetime, timedelta
from config.config import SOURCE_NAME_MAP

# 配置日志
logger = logging.getLogger(__name__)

def fetch_hotspot(source, base_url):
    """
    从指定源获取热点数据
    """
    try:
        # 从环境变量获取limit值，默认为1
        limit = os.getenv('HOTSPOT_LIMIT', '1')
        url = f"{base_url}/{source}?limit={limit}"
        response = requests.get(url, timeout=10, allow_redirects=True)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 200:
            return data.get("data", [])
        else:
            logger.error(f"获取 {source} 数据失败: {data.get('message', '未知错误')}")
            return []
    except Exception as e:
        logger.error(f"获取 {source} 数据时发生错误: {str(e)}")
        return []

def collect_all_hotspots(sources, base_url):
    """
    收集所有指定源的热点数据
    """
    all_hotspots = []
    
    for source in sources:
        logger.info(f"正在获取 {source} 的热点数据...")
        hotspots = fetch_hotspot(source, base_url)
        
        for item in hotspots:
            # 确保每个热点都有标题和链接
            if "title" in item and "url" in item:
                # 构建热点数据，保留desc字段
                hotspot_data = {
                    "title": item["title"],
                    "url": item["url"],
                    "source": source,
                    "hot": item.get("hot", ""),
                    "time": item.get("time", ""),
                    "timestamp": item.get("timestamp", ""),
                }
                
                # 如果有摘要，保留摘要
                if "desc" in item and item["desc"]:
                    hotspot_data["desc"] = item["desc"]
                    
                all_hotspots.append(hotspot_data)
    
    logger.info(f"共收集到 {len(all_hotspots)} 条热点数据")
    return all_hotspots

def fetch_rss_articles(rss_url, days=1):
    """
    从RSS源获取最近指定天数内的文章
    """
    try:
        logger.info(f"正在获取RSS源: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        if feed.bozo:  # 检查feed解析是否有错误
            logger.warning(f"RSS解析警告: {feed.bozo_exception}")
        
        articles = []
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(days=days)
        
        for entry in feed.entries:
            # 尝试获取发布时间
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_time = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            else:
                # 如果没有时间信息，假设是最近的
                pub_time = current_time
            
            # 获取作者信息作为来源
            source = "公众号精选"
            if hasattr(entry, 'author') and entry.author:
                source = f"{entry.author}"
            
            # 只保留最近days天的文章
            if pub_time >= cutoff_time:
                articles.append({
                    "title": entry.title,
                    "url": entry.link,
                    "source": source,
                    "hot": "",
                    "published": pub_time.strftime("%Y-%m-%d %H:%M:%S")
                })
        
        logger.info(f"从RSS源获取到 {len(articles)} 篇最近{days}天的文章")
        return articles
    except Exception as e:
        logger.error(f"获取RSS源时发生错误: {str(e)}")
        return []

def filter_recent_hotspots(hotspots, days=1):
    """
    筛选时间范围内的热点数据
    时间范围：昨天整天 + 今天到当前时间
    """
    filtered_hotspots = []
    current_time = datetime.now()
    
    # 设置时间范围：昨天0点到现在
    yesterday = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    
    logger.info(f"当前时间: {current_time}, 筛选时间范围: {yesterday} 至 {current_time}")
    
    for item in hotspots:
        # 尝试解析时间戳
        timestamp = item.get("timestamp") or item.get("time", "")
        
        if timestamp:
            try:
                # 将时间戳转换为datetime对象
                if isinstance(timestamp, str):
                    if 'T' in timestamp and ('Z' in timestamp or '+' in timestamp):
                        # ISO格式: 2025-03-08T12:04:22.020Z
                        item_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        # 尝试作为数字处理
                        timestamp = float(timestamp)
                        # 毫秒级时间戳转换为秒级时间戳
                        if timestamp > 9999999999:
                            timestamp = timestamp / 1000
                        item_time = datetime.fromtimestamp(timestamp)
                else:
                    # 数字类型时间戳
                    if timestamp > 9999999999:  # 毫秒级时间戳
                        timestamp = timestamp / 1000
                    item_time = datetime.fromtimestamp(float(timestamp))
                
                # 检查时间是否在未来（可能是错误的时间戳）
                if item_time > current_time + timedelta(hours=1):
                    # 可能是未来的时间戳，尝试调整年份
                    logger.warning(f"检测到未来时间戳: {item_time}, 标题: {item['title']}")
                    
                    # 如果时间戳对应的年份是未来年份，调整为当前年份
                    if item_time.year > current_time.year:
                        adjusted_year = current_time.year
                        try:
                            item_time = item_time.replace(year=adjusted_year)
                            logger.info(f"调整时间戳年份为当前年份: {item_time}")
                        except ValueError as e:
                            logger.warning(f"调整时间戳年份失败: {str(e)}")
                
                # 记录解析结果
                logger.info(f"热点: {item['title'][:30]}..., 时间: {item_time}")
                
                # 只保留昨天0点到现在的热点
                if yesterday <= item_time <= current_time:
                    filtered_hotspots.append(item)
                    continue
                else:
                    logger.info(f"丢弃时间范围外热点: {item['title']}, 时间: {item_time}")
                    continue
            except (ValueError, TypeError) as e:
                logger.warning(f"解析时间戳失败: {timestamp}, 错误: {str(e)}, 标题: {item['title']}")
        
        # 如果没有有效的时间戳或解析失败，默认保留该条目
        logger.info(f"无有效时间戳，默认保留: {item['title']}")
        filtered_hotspots.append(item)
    
    logger.info(f"筛选后保留 {len(filtered_hotspots)}/{len(hotspots)} 条时间范围内的热点数据")
    return filtered_hotspots