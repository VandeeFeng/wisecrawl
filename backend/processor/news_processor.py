import asyncio
import logging
import json
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

from utils.utils import get_content_hash, load_summary_cache, save_summary_cache, get_project_root
from crawler.web_crawler import fetch_webpage_content, extract_publish_time_from_html
from llm_integration.content_integration import summarize_with_tencent_hunyuan

# Configure logging
logger = logging.getLogger(__name__)

# Define constants for summary length control
FINAL_DESC_MAX_LENGTH = 150
FALLBACK_DESC_LENGTH = 150
MIN_CONTENT_LENGTH_FOR_SUMMARY = 50 # Min content length to attempt summary

async def process_hotspot_with_summary(hotspots, hunyuan_api_key, max_workers=5, tech_only=False, use_cache=True):
    """
    Process hotspot data asynchronously, get webpage content and generate summaries
    Prioritize using API returned summaries, only call Hunyuan model when no summary exists
    Also try to extract publish time from webpage content
    If tech_only is True, only keep tech-related content
    Support cache mechanism to avoid processing same content repeatedly
    Update merged file directly after processing
    """
    enhanced_hotspots = []
    
    # Get original merged file path
    merged_file_path = None
    if hotspots and len(hotspots) > 0 and "saved_at" in hotspots[0]:
        saved_time = hotspots[0]["saved_at"]
        try:
            # Extract timestamp from saved_at field
            dt = datetime.fromisoformat(saved_time.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H-%M-%S")
            # Get project root directory
            project_root = get_project_root()
            # Build absolute path from project root
            merged_file_path = os.path.join(project_root, "data", "merged", f"hotspots_{date_str}_{time_str}.jsonl")
            logger.info(f"Found original merged file: {merged_file_path}")
        except Exception as e:
            logger.warning(f"Could not extract timestamp from saved_at: {str(e)}")
    
    def process_single_item(item):
        url = item["url"]
        title = item.get("title", "未知标题")
        source = item.get("source", "未知来源")
        content = item.get("content", "")  # 可能从RSS预提取的内容
        
        # 初始化标记
        has_content = bool(content and len(content.strip()) > MIN_CONTENT_LENGTH_FOR_SUMMARY)
        has_timestamp = bool(item.get("timestamp") or item.get("time") or item.get("extracted_time"))
        
        # --- 1. 确定是否需要抓取网页 ---
        needs_content = True  # 总是需要获取内容用于生成摘要
        needs_timestamp = not has_timestamp
        needs_fetching = needs_content or needs_timestamp
        
        # --- 2. Twitter源特殊处理 ---
        # Get the source safely
        if source.startswith("Twitter"):
            if needs_fetching: # Log only if it *would* have fetched
                logger.info(f"强制跳过抓取，来源为 Twitter: {title}")
            needs_fetching = False # Override: Twitter posts never need fetching
        
        # --- 3. Fetch Web Content (HTML and potentially Content) if Necessary ---
        fetched_content = None # Store content specifically from fetching
        if needs_fetching:
            log_reason = []
            if needs_content: log_reason.append("需要获取内容用于生成摘要")
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
        
        # --- 5. Generate AI Summary ---
        summary_result_ai = {"summary": "", "is_tech": False} # For AI result
        final_summary = "" # Initialize empty final summary
        is_tech_final = item.get("is_tech", tech_only) # Default tech status
        summary_source = "未知" # Track the source of our summary

        # 尝试使用AI生成摘要
        if has_content:
            try:
                # 使用腾讯混元生成摘要
                summary_result_ai = summarize_with_tencent_hunyuan(
                    content, hunyuan_api_key, title=title, use_cache=use_cache
                )
                
                if summary_result_ai and summary_result_ai.get("summary"):
                    final_summary = summary_result_ai["summary"]
                    is_tech_final = summary_result_ai.get("is_tech", tech_only)
                    summary_source = "AI生成"
                    logger.info(f"成功使用AI生成摘要: {title}")
                else:
                    logger.warning(f"AI未能生成有效摘要: {title}")
                    # 使用内容截断作为备选
                    try:
                        soup = BeautifulSoup(content, 'html.parser')
                        plain_text = soup.get_text(strip=True)
                        if len(plain_text) > FALLBACK_DESC_LENGTH:
                            final_summary = plain_text[:FALLBACK_DESC_LENGTH] + "..."
                        else:
                            final_summary = plain_text
                            summary_source = "内容截断(AI失败)"
                            logger.info(f"使用内容截断作为备选摘要: {title}")
                    except Exception as fallback_e:
                        logger.error(f"内容截断备选方案失败: {fallback_e}, 标题: {title}")
                        final_summary = "[摘要生成失败]"
                        summary_source = "处理失败"
            except Exception as e:
                logger.error(f"混元摘要生成失败: {e}, 标题: {title}. 将使用内容截断作为备选。")
                # 使用内容截断作为备选
                try:
                    soup = BeautifulSoup(content, 'html.parser')
                    plain_text = soup.get_text(strip=True)
                    if len(plain_text) > FALLBACK_DESC_LENGTH:
                        final_summary = plain_text[:FALLBACK_DESC_LENGTH] + "..."
                    else:
                        final_summary = plain_text
                        summary_source = "内容截断(AI失败)"
                        logger.info(f"使用内容截断作为备选摘要: {title}")
                except Exception as fallback_e:
                    logger.error(f"内容截断备选方案失败: {fallback_e}, 标题: {title}")
                    final_summary = "[摘要生成失败]"
                    summary_source = "处理失败"
        else:
            logger.warning(f"没有足够的内容生成摘要: {title}")
            final_summary = "[摘要无法生成：无内容或来源信息不足]"
            summary_source = "无内容"

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
        
        # 直接使用gather的结果
        completed_results = await asyncio.gather(*tasks)
        for result in completed_results:
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