#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻处理函数：对所有新闻信息合并和筛选处理，输出为可以被模型调用的格式；
对模型输出的格式进行格式处理以方便下游使用
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from utils.utils import get_content_hash, load_summary_cache, save_summary_cache
from crawler.web_crawler import fetch_webpage_content, extract_publish_time_from_html

# 配置日志
logger = logging.getLogger(__name__)

async def process_hotspot_with_summary(hotspots, hunyuan_api_key, max_workers=5, tech_only=False, use_cache=True):
    """
    异步处理热点数据，获取网页内容并生成摘要
    优先使用API返回的摘要，没有摘要时才调用混元模型
    同时尝试从网页内容中提取发布时间
    如果tech_only为True，则只保留科技相关的内容
    支持缓存机制，避免重复处理相同内容
    处理后直接更新merged文件
    """
    enhanced_hotspots = []
    
    # 获取原始merged文件路径
    merged_file_path = None
    if hotspots and len(hotspots) > 0 and "saved_at" in hotspots[0]:
        saved_time = hotspots[0]["saved_at"]
        try:
            # 从saved_at字段提取时间戳
            dt = datetime.fromisoformat(saved_time.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H-%M-%S")
            # 获取当前脚本所在目录的绝对路径
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # 构建绝对路径
            merged_file_path = os.path.join(script_dir, "data", "merged", f"hotspots_{date_str}_{time_str}.jsonl")
            logger.info(f"找到原始merged文件: {merged_file_path}")
        except Exception as e:
            logger.warning(f"无法从saved_at提取时间戳: {str(e)}")
    
    async def process_single_item(item):
        url = item["url"]
        logger.info(f"开始处理: {item['title']} ({url})")
        
        # 检查是否已有摘要
        has_summary = item.get("desc") and len(item.get("desc", "").strip()) > 20
        
        # 检查是否已有时间戳
        has_timestamp = item.get("timestamp") or item.get("time", "")
        
        # 如果同时有摘要和时间戳，直接使用
        if has_summary and has_timestamp:
            logger.info(f"使用API返回的摘要和时间戳: {item['title']}")
            # 默认不知道是否科技相关，设为True以避免过滤
            return {**item, "content": "", "summary": item["desc"], "is_tech": True, "is_processed": True}
        
        # 获取网页内容和原始HTML
        content, html_content = fetch_webpage_content(url)
        summary_result = {"summary": "", "is_tech": False}
        
        # 如果没有时间戳，尝试从HTML中提取
        if not has_timestamp and html_content:
            publish_time = extract_publish_time_from_html(html_content, url)
            if publish_time:
                logger.info(f"从HTML中提取到发布时间: {publish_time}, 标题: {item['title']}")
                # 添加提取到的时间戳
                item["extracted_time"] = publish_time.isoformat()
                item["timestamp"] = int(publish_time.timestamp() * 1000)  # 转换为毫秒级时间戳
        
        # 如果没有摘要但有内容，生成摘要
        if not has_summary and content:
            from llm_integration.hunyuan_integration import summarize_with_tencent_hunyuan
            summary_result = summarize_with_tencent_hunyuan(content, hunyuan_api_key, use_cache=use_cache)
        elif has_summary:
            # 如果已有摘要，默认设置为科技相关（避免过滤）
            summary_result = {"summary": item["desc"], "is_tech": True}
            
        result = {
            **item, 
            "content": content, 
            "summary": summary_result["summary"],
            "is_tech": summary_result["is_tech"],
            "is_processed": True  # 添加处理标记
        }
        
        logger.info(f"处理完成: {item['title']}, 摘要长度: {len(result['summary'])}, 科技相关: {result['is_tech']}")
        return result
    
    # 使用线程池执行网页内容获取和摘要生成
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                lambda i=i: process_single_item(i)
            )
            for i in hotspots
        ]
        
        completed_tasks = await asyncio.gather(*tasks)
        for completed_task in completed_tasks:
            result = await completed_task
            # 如果tech_only为True，只保留科技相关的内容
            if not tech_only or result.get("is_tech", False):
                enhanced_hotspots.append(result)
    
    # 记录处理结果统计
    with_summary = sum(1 for item in enhanced_hotspots if item.get("summary"))
    with_timestamp = sum(1 for item in enhanced_hotspots if item.get("timestamp") or item.get("time") or item.get("extracted_time"))
    tech_related = sum(1 for item in enhanced_hotspots if item.get("is_tech", False))
    
    logger.info(f"热点处理完成: 总计 {len(enhanced_hotspots)} 条, 成功生成摘要 {with_summary} 条, 有时间戳 {with_timestamp} 条, 科技相关 {tech_related} 条")
    
    # 如果找到了原始merged文件，直接更新
    if merged_file_path and os.path.exists(merged_file_path):
        try:
            # 创建一个ID到处理结果的映射
            processed_items = {item["url"]: item for item in enhanced_hotspots}
            
            # 读取原始文件并更新
            updated_lines = []
            with open(merged_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        url = item.get("url", "")
                        if url in processed_items:
                            # 更新已处理的项目
                            updated_item = processed_items[url]
                            # 只保留需要的字段，不包括content等大字段
                            updated_item_clean = {k: v for k, v in updated_item.items() 
                                               if k not in ["content"]}
                            updated_lines.append(json.dumps(updated_item_clean, ensure_ascii=False))
                        else:
                            # 保持原有项目不变
                            updated_lines.append(line.strip())
            
            # 写回文件
            with open(merged_file_path, 'w', encoding='utf-8') as f:
                for line in updated_lines:
                    f.write(line + '\n')
            
            logger.info(f"已更新merged文件: {merged_file_path}")
        except Exception as e:
            logger.error(f"更新merged文件失败: {str(e)}")
    
    return enhanced_hotspots

# 导入os模块，用于文件路径操作
import os