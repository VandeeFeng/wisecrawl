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
FINAL_DESC_MAX_LENGTH = 150
FALLBACK_DESC_LENGTH = 150
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
        
        # --- 1. Check if Initial Desc is Valid (Basic Check) ---
        # Remove the preliminary truncation. Only check if desc exists and is reasonably long.
        # The actual truncation, if needed as a fallback, happens later.
        # has_summary_after_check = bool(desc and len(desc.strip()) > 10)
        # Let's refine this slightly: consider desc valid if it exists and isn't just whitespace
        is_initial_desc_present_and_valid = bool(desc and len(desc.strip()) > 10) # Keep the minimum length check

        # --- 2. Determine necessity of fetching HTML --- 
        # Use the validity check from step 1
        # has_summary_after_check = is_initial_desc_present_and_valid 
        # Rename has_summary_after_check for clarity as it's based on initial desc
        has_valid_initial_desc = is_initial_desc_present_and_valid

        has_content = bool(content and len(content.strip()) > MIN_CONTENT_LENGTH_FOR_SUMMARY)
        has_timestamp = bool(item.get("timestamp") or item.get("time"))

        # Define conditions for fetching HTML
        # Need content fetch if we *don't* have a valid initial desc AND we *don't* have enough content already.
        needs_content = not has_valid_initial_desc and not has_content 
        needs_timestamp = not has_timestamp
        needs_fetching = needs_content or needs_timestamp

        # ---> ADD THIS CHECK FOR TWITTER <---
        source = item.get("source", "") # Get the source safely
        if source.startswith("Twitter"):
            if needs_fetching: # Log only if it *would* have fetched
                logger.info(f"强制跳过抓取，来源为 Twitter: {title}")
            needs_fetching = False # Override: Twitter posts never need fetching
        # ---> END OF TWITTER CHECK <---

        # --- 3. Fetch Web Content (HTML and potentially Content) if Necessary ---
        fetched_content = None # Store content specifically from fetching
        if needs_fetching:
            log_reason = []
            if needs_content: log_reason.append("缺少内容/有效摘要")
            if needs_timestamp: log_reason.append("缺少时间戳")
            logger.info(f"需要抓取网页 ({', '.join(log_reason)}): {title}")
            # Fetch both content and HTML if needed. 
            # If fetch fails, content might remain original, html_content might be None.
            try:
                fetched_content, html_content = fetch_webpage_content(url, existing_content=content)
                if fetched_content and fetched_content != content: # Update content only if fetch provided new content
                    logger.info(f"网页抓取成功，获取到新内容: {title}")
                    content = fetched_content 
                    has_content = bool(content and len(content.strip()) > MIN_CONTENT_LENGTH_FOR_SUMMARY)
                elif html_content:
                    logger.info(f"网页抓取成功，获取到HTML (内容未变或抓取失败): {title}")
                else:
                     logger.warning(f"网页抓取未能获取到有效内容或HTML: {title}")
            except Exception as fetch_err:
                 logger.error(f"抓取网页时发生错误: {fetch_err}, URL: {url}")
                 # Keep original content, html_content remains None

        # ---> 在这里重新计算 has_content <--- 
        has_content = bool(content and len(content.strip()) > MIN_CONTENT_LENGTH_FOR_SUMMARY)
        logger.info(f"抓取尝试后(如果需要)，内容状态: has_content={has_content}, 长度={len(content.strip() if content else '')} for {title}")

        # --- 4. Extract Timestamp if Necessary (using potentially fetched HTML) ---
        if needs_timestamp: # Check if we *needed* it, even if fetch failed
            if html_content: # Proceed only if we successfully got html
                publish_time = extract_publish_time_from_html(html_content, url)
                if publish_time:
                    logger.info(f"从HTML中提取到发布时间: {publish_time}, 标题: {title}")
                    item["extracted_time"] = publish_time.isoformat()
                    item["timestamp"] = int(publish_time.timestamp() * 1000)
                    has_timestamp = True # Mark timestamp as now available
                else:
                     logger.info(f"未能在HTML中找到发布时间: {title}")
            else:
                 # Log only if we NEEDED the timestamp but couldn't get HTML
                 logger.warning(f"需要时间戳但无法获取HTML内容: {title}")
        
        # --- 5. Attempt AI Summary or Use Fallback ---
        # Use the state *after* potential HTML fetching
        summary_result_ai = {"summary": "", "is_tech": False} # For AI result
        # Initialize final_summary with the *original* desc. Fallbacks will overwrite if needed.
        final_summary = item.get("desc", "") # Use item.get to ensure we have the original
        is_tech_final = item.get("is_tech", tech_only) # Default tech status
        # Reset summary_source, it will be set based on the actual outcome
        summary_source = "未知" # Set to unknown initially

        # Decide if AI summary is needed: only if initial desc was invalid
        if not has_valid_initial_desc:
            # Check content availability *after* potential fetching
            # This check correctly happens after step 3, so 'has_content' reflects fetch results
            if has_content: 
                logger.info(f"无有效原始摘要，尝试使用混元生成摘要: {title}")
                try:
                    # Call Hunyuan API (using potentially updated content)
                    summary_result_ai = summarize_with_tencent_hunyuan(content, hunyuan_api_key, title=title, use_cache=use_cache)
                    final_summary = summary_result_ai.get("summary", "")
                    is_tech_final = summary_result_ai.get("is_tech", tech_only)
                    if final_summary:
                         summary_source = "混元AI生成"
                         logger.info(f"混元摘要生成成功: {title}")
                    else:
                         summary_source = "混元AI返回空"
                         logger.warning(f"混元摘要生成返回空: {title}")
                         raise ValueError("AI returned empty summary") # Trigger fallback

                except Exception as e:
                    logger.error(f"混元摘要生成失败: {e}, 标题: {title}. 将使用内容截断作为备选。")
                    summary_source = "内容截断(AI失败)"
                    # Fallback logic: truncate potentially updated content
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
                # No summary (initially invalid) and no content even after fetching
                logger.warning(f"无有效摘要且无内容，无法生成摘要: {title}")
                # --- Modified Fallback Logic ---
                original_desc = item.get("desc", "") # Get the original desc passed from data_collector
                if original_desc and len(original_desc.strip()) > 5: # Check if original desc had *some* text
                    final_summary = original_desc[:FALLBACK_DESC_LENGTH] + "..." if len(original_desc) > FALLBACK_DESC_LENGTH else original_desc
                    summary_source = "原始摘要截断(内容抓取失败)"
                    logger.info(f"使用原始摘要截断作为最终备选: {title}")
                else: # Original desc was also empty or too short
                    final_summary = "[摘要无法生成：无内容或来源信息不足]" # More descriptive message
                    summary_source = "无内容失败(原始摘要亦空)"
                # --- End of Modified Fallback Logic ---
                is_tech_final = tech_only # Default
                # summary_source is set inside the if/else
        else:
             # Initial desc was valid
             logger.info(f"使用来自源的有效摘要作为基础: {title}")
             # Keep the initially determined final_summary (which is the original desc)
             if len(final_summary) > FALLBACK_DESC_LENGTH:
                final_summary = final_summary[:FALLBACK_DESC_LENGTH] + "..."
             summary_source = "原始提供" # Source is the original description
             # Keep is_tech as potentially determined by RSS stage or default
             is_tech_final = item.get("is_tech", tech_only)

        # --- 6. Assemble Final Result ---
        result = {
            **item,
            "content": content, # Keep potentially updated content
            "summary": final_summary, # Use the final determined summary
            "is_tech": is_tech_final,
            "summary_source": summary_source, # Track the final source
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