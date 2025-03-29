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
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

from utils.utils import get_content_hash, load_summary_cache, save_summary_cache
from crawler.web_crawler import fetch_webpage_content, extract_publish_time_from_html
from llm_integration.hunyuan_integration import summarize_with_tencent_hunyuan

# 配置日志
logger = logging.getLogger(__name__)

# Define constants for summary length control
FINAL_DESC_MAX_LENGTH = 300
FALLBACK_DESC_LENGTH = 500
MIN_CONTENT_LENGTH_FOR_SUMMARY = 50 # Min content length to attempt summary

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
        title = item.get('title', '[无标题]')
        logger.info(f"开始处理: {title} ({url})")
        
        # Initialize variables
        desc = item.get("desc", "")
        content = item.get("content", "")
        html_content = None # Initialize html_content
        summary_source = "原始提供" # Track where the summary came from
        
        # --- 1. Strict Length Check and Truncation for Initial Desc ---
        if desc and len(desc.strip()) > FINAL_DESC_MAX_LENGTH:
            original_length = len(desc)
            desc = desc[:FINAL_DESC_MAX_LENGTH] + "..." # Truncate immediately
            summary_source = f"原始截断(>{FINAL_DESC_MAX_LENGTH})"
            logger.info(f"原始 desc 过长 ({original_length} > {FINAL_DESC_MAX_LENGTH})，已截断: {title}")
        
        # Check if we have a valid summary AFTER potential truncation
        has_summary = bool(desc and len(desc.strip()) > 10) 
        has_content = bool(content and len(content.strip()) > MIN_CONTENT_LENGTH_FOR_SUMMARY)
        has_timestamp = bool(item.get("timestamp") or item.get("time"))

        # --- 2. Fetch Web Content if Necessary ---
        # Fetch content only if we don't have a valid summary YET
        # AND content is missing/insufficient.
        # Note: If summary was truncated, has_summary is True, so we won't fetch content here unnecessarily.
        if not has_summary and not has_content:
            logger.info(f"缺少摘要和足够内容，尝试抓取网页: {title}")
            content, html_content = fetch_webpage_content(url, existing_content=content)
            has_content = bool(content and len(content.strip()) > MIN_CONTENT_LENGTH_FOR_SUMMARY)
            if not has_content:
                 logger.warning(f"抓取网页后仍无法获取足够内容: {title}")
        elif not has_content and has_summary:
             # We have a summary but no content, might still want content for consistency or timestamp
             logger.info(f"有摘要但无内容，尝试抓取网页以获取完整内容/时间戳: {title}")
             _, html_content = fetch_webpage_content(url, existing_content=content)
             # Keep original content if fetch fails to get new content

        # --- 3. Extract Timestamp if Necessary ---
        if not has_timestamp:
            if not html_content and has_content: # If we have content but didn't fetch html, try fetching html now
                 logger.info(f"尝试抓取HTML以提取时间戳: {title}")
                 _, html_content = fetch_webpage_content(url, existing_content=content, fetch_html_only=True)
                 
            if html_content: # Proceed only if we have html
                publish_time = extract_publish_time_from_html(html_content, url)
                if publish_time:
                    logger.info(f"从HTML中提取到发布时间: {publish_time}, 标题: {title}")
                    item["extracted_time"] = publish_time.isoformat()
                    item["timestamp"] = int(publish_time.timestamp() * 1000)
                else:
                     logger.info(f"未能在HTML中找到发布时间: {title}")
            else:
                 logger.warning(f"无法获取HTML内容以提取时间戳: {title}")

        # --- 4. Attempt AI Summary or Use Fallback ---
        summary_result_ai = {"summary": "", "is_tech": False} # For AI result
        final_summary = desc # Start with the potentially valid desc from RSS
        is_tech_final = item.get("is_tech", tech_only) # Default tech status

        if not has_summary:
            if has_content:
                logger.info(f"无有效摘要，尝试使用混元生成摘要: {title}")
                try:
                    # Call Hunyuan API
                    summary_result_ai = summarize_with_tencent_hunyuan(content, hunyuan_api_key, title=title, use_cache=use_cache)
                    final_summary = summary_result_ai.get("summary", "")
                    is_tech_final = summary_result_ai.get("is_tech", tech_only)
                    if final_summary:
                         summary_source = "混元AI生成"
                         logger.info(f"混元摘要生成成功: {title}")
                    else:
                         summary_source = "混元AI返回空"
                         logger.warning(f"混元摘要生成返回空: {title}")
                         # Fallback even if AI returns empty
                         raise ValueError("AI returned empty summary") 

                except Exception as e:
                    logger.error(f"混元摘要生成失败: {e}, 标题: {title}. 将使用内容截断作为备选。")
                    summary_source = "内容截断(AI失败)"
                    # Fallback logic: truncate content
                    try:
                        soup = BeautifulSoup(content, 'html.parser')
                        plain_text = soup.get_text(strip=True)
                        if len(plain_text) > FALLBACK_DESC_LENGTH:
                            final_summary = plain_text[:FALLBACK_DESC_LENGTH] + "..."
                        else:
                            final_summary = plain_text
                        is_tech_final = tech_only # Default tech status on fallback
                        logger.info(f"已生成备选摘要 (截断内容): {title}")
                    except Exception as fallback_e:
                         logger.error(f"内容截断备选方案失败: {fallback_e}, 标题: {title}")
                         final_summary = "[摘要生成失败]"
                         is_tech_final = tech_only
                         summary_source = "处理失败"
            else:
                # No summary and no content even after fetching
                logger.warning(f"无摘要且无内容，无法生成摘要: {title}")
                final_summary = "[摘要无法生成：无内容]"
                is_tech_final = tech_only # Default
                summary_source = "无内容失败"
        else:
             # Summary was valid from the start (passed length check)
             logger.info(f"使用来自源的有效摘要: {title}")
             # Keep is_tech as potentially determined by RSS stage or default
             is_tech_final = item.get("is_tech", tech_only)

        # --- 5. Assemble Final Result ---
        result = {
            **item,
            "content": content, # Keep full content for potential later use, even if long
            "summary": final_summary, # Use the final determined summary
            "desc": final_summary, # Ensure desc field also has the final summary
            "is_tech": is_tech_final,
            "summary_source": summary_source, # Add source info for debugging
            "is_processed": True
        }
        
        logger.info(f"处理完成: {title}, 摘要来源: {summary_source}, 摘要长度: {len(final_summary)}, 科技相关: {is_tech_final}")
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