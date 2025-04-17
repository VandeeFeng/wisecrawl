import os
import json
import time
import logging
import requests
from datetime import datetime
from config.config import SOURCE_NAME_MAP, DEEPSEEK_MODEL_ID
from utils.utils import format_title_for_display, get_project_root
from utils.token_tracker import token_tracker

logger = logging.getLogger(__name__)

def summarize_with_deepseek(hotspots, api_key, api_url=None, model_id=None, max_retries=3, tech_only=False):
    """
    使用Deepseek API对热点进行汇总归类，支持重试
    根据tech_only参数使用不同的prompt
    """
    if api_url is None:
        api_url = "http://127.0.0.1:11434/v1/chat/completions"
    
    if model_id is None:
        model_id = DEEPSEEK_MODEL_ID
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            simplified_hotspots = []
            for idx, item in enumerate(hotspots):
                source_name = SOURCE_NAME_MAP.get(item['source'], item['source'])
                simplified_hotspots.append({
                    "id": idx,
                    "title": item['title'],
                    "source": source_name,
                    "summary": item.get('summary', '')  
                })
            
            hotspot_dict = {idx: item for idx, item in enumerate(hotspots)}
            
            hotspot_json = json.dumps(simplified_hotspots, ensure_ascii=False)
            
            # Get project root directory
            project_root = get_project_root()
            # Build absolute paths from project root
            save_directory = os.path.join(project_root, "data", "inputs")
            os.makedirs(save_directory, exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%H-%M-%S")
            input_filename = os.path.join(save_directory, f"deepseek_input_{today}_{timestamp}.json")
            with open(input_filename, 'w', encoding='utf-8') as f:
                f.write(hotspot_json)
            logger.info(f"已保存Deepseek输入数据至 {input_filename}")
            
            if tech_only:
                prompt = f"""
                以下是今日科技热点信息列表（包含新闻和社交媒体帖子，JSON格式），部分条目包含内容摘要：
                {hotspot_json}
                请总结出10条最重要的科技新闻，优先选择AI相关新闻，去除重复和无关内容。
                重点关注最新发布的AI技术或者模型等，相关新闻在返回的结果排序中需要前置；公众号的文章权重更高，其余结果按重要性排序。
                你需要将相似的新闻合并为一条，并提供一个直观简洁的中文标题，需要讲清楚新闻内容不要太泛化（不超过30个字）。
                同时，也请关注来自 Twitter 等社交媒体源 (source: Twitter) 的重要信息，特别是关于最新 AI 技术突破、模型发布或重要行业动态的帖子，它们同样具有很高的价值。
                相关新闻的ID列表最多选择其中4条，取最典型的，超过数量不需要全部给出。请特别注意，如果同一家媒体在多个渠道发布相同的内容，或新闻标题相似度极高，不要同时选择，则仅需列出1条即可。
                如果有摘要信息，请参考摘要提供更准确的标题。
                
                请以JSON格式返回结果，格式如下：
                ```json
                [
                  {{
                    "title": "热点标题",
                    "related_ids": [相关热点的ID列表]
                  }},
                  ...
                ]
                ```
                
                只返回JSON数据，不要有任何额外说明。
                """
            else:
                prompt = f"""
                以下是今日热点信息列表（包含新闻和社交媒体帖子，JSON格式），部分条目包含内容摘要：
                {hotspot_json}
                请总结出10条最重要的热点新闻，优先选择科技和AI相关新闻，但也要包含其他领域（如社会、娱乐、体育等）的重要新闻，去除重复内容。
                你需要将相似的新闻合并为一条，并提供一个直观简洁的中文标题，需要讲清楚新闻内容不要太泛化（不超过30个字）。
                同时，也请关注来自 Twitter 等社交媒体源 (source: Twitter) 的重要信息，特别是关于最新 AI 技术突破、模型发布或重要行业动态的帖子，将它们与新闻同等对待进行筛选和总结。
                相关新闻的ID列表最多选择其中4条，取最典型的，超过数量不需要全部给出。请特别注意，如果同一家媒体在多个渠道发布相同的内容，或新闻标题相似度极高，不要同时选择，则仅需列出1条即可。
                如果有摘要信息，请参考摘要提供更准确的标题。
                
                请以JSON格式返回结果，格式如下：
                ```json
                [
                  {{
                    "title": "热点标题",
                    "related_ids": [相关热点的ID列表]
                  }},
                  ...
                ]
                ```
                
                只返回JSON数据，不要有任何额外说明。
                """
            
            try:
                logger.info(f"正在调用 Deepseek API，尝试次数: {retry_count + 1}/{max_retries}")
                
                payload = {
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的新闻编辑助手，擅长归纳总结热点新闻。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
                
                import subprocess
                import tempfile
                
                payload_json = json.dumps(payload, ensure_ascii=False)
                
                with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', suffix='.json', delete=False) as temp:
                    temp_path = temp.name
                    temp.write(payload_json)
                
                try:
                    curl_cmd = [
                        'curl', '-s', '-X', 'POST',
                        '-H', f'Authorization: Bearer {api_key}',
                        '-H', 'Content-Type: application/json',
                        '-d', f'@{temp_path}',
                        '--insecure',  
                        api_url
                    ]
                    
                    logger.info(f"执行curl命令: {' '.join(curl_cmd).replace(api_key, '***')}")
                    
                    process = subprocess.run(
                        curl_cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                        encoding='utf-8'
                    )
                    
                    if process.returncode != 0:
                        raise Exception(f"curl命令执行失败，返回码: {process.returncode}, 错误: {process.stderr}")
                    
                    result = json.loads(process.stdout)
                    
                    if "choices" not in result or len(result["choices"]) == 0:
                        raise Exception(f"API响应格式不正确: {process.stdout[:200]}...")
                    
                    # Track token usage for Deepseek model
                    if "usage" in result:
                        usage = result["usage"]
                        token_tracker.add_usage(
                            model_id,
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0)
                        )
                    
                    logger.info("API调用成功!")
                    
                finally:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                
            except Exception as e:
                logger.error(f"调用Deepseek API时发生错误: {str(e)}")
                logger.error(f"错误类型: {type(e)}")
                
                import traceback
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"将在3秒后重试...")
                    time.sleep(3)
                    continue
                else:
                    raise
            
            json_response = result["choices"][0]["message"]["content"]
            
            json_str = json_response
            if "```json" in json_response:
                json_str = json_response.split("```json")[1].split("```")[0].strip()
            
            output_directory = os.path.join(project_root, "data", "outputs")
            os.makedirs(output_directory, exist_ok=True)
            
            raw_output_filename = os.path.join(output_directory, f"deepseek_raw_response_{today}_{timestamp}.json")
            with open(raw_output_filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存Deepseek原始响应至 {raw_output_filename}")
            
            output_filename = os.path.join(output_directory, f"deepseek_output_{today}_{timestamp}.json")
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"已保存Deepseek输出数据至 {output_filename}")
            
            try:
                news_items = json.loads(json_str)
                
                formatted_summary = ""
                for index, news in enumerate(news_items[:20]):
                    num = str(index + 1).zfill(2)
                    title = news.get("title", "未知标题")
                    
                    formatted_summary += f"## ** {num} {title} **  \n"
                    
                    news_summary = ""
                    related_ids = news.get("related_ids", [])
                    
                    all_summaries = []
                    for news_id in related_ids:
                        if news_id in hotspot_dict:
                            item = hotspot_dict[news_id]
                            if item.get("summary") and len(item.get("summary").strip()) > 20:  
                                all_summaries.append(item.get("summary"))
                    
                    if all_summaries:
                        best_summary = sorted(all_summaries, key=len, reverse=True)[0]
                        if len(best_summary) > 100:
                            news_summary = best_summary[:97] + "..."
                        else:
                            news_summary = best_summary
                    
                    if not news_summary:
                        news_summary = f"{title}相关信息，详情请查看以下链接。"
                    
                    formatted_summary += f"{news_summary}\n\n"
                    
                    for news_id in related_ids:
                        if news_id in hotspot_dict:
                            item = hotspot_dict[news_id]
                            source_name = SOURCE_NAME_MAP.get(item.get('source', 'unknown'), item.get('source', 'unknown'))
                            item_title = item.get('title', '未知标题')
                            
                            item_title = item_title.replace('\n', ' ').replace('\r', ' ')
                            item_title = ' '.join(item_title.split())
                            
                            url = item.get('url', '#')
                            if not url or url == "#":
                                if "Twitter" in source_name:
                                    username = source_name.replace("Twitter-", "").strip()
                                    username_no_space = username.replace(" ", "")  # 移除空格
                                    
                                    # 推文URL格式应为 https://twitter.com/username/status/tweet_id
                                    # 由于我们没有真实的tweet_id，所以只能指向用户主页
                                    url = f"https://twitter.com/{username_no_space}"
                                else:
                                    url = "#"  
                            
                            formatted_summary += f"- [{item_title}]({url}) `🏷️{source_name}`\n"
                    
                    formatted_summary += "\n"
                
                summary_filename = os.path.join(output_directory, f"formatted_summary_{today}_{timestamp}.md")
                with open(summary_filename, 'w', encoding='utf-8') as f:
                    f.write(formatted_summary)
                logger.info(f"已保存格式化摘要至 {summary_filename}")
                
                return formatted_summary
                
            except json.JSONDecodeError as e:
                logger.error(f"解析Deepseek返回的JSON失败: {str(e)}")
                return f"解析Deepseek返回的JSON失败: {str(e)}"
            
        except requests.exceptions.Timeout:
            retry_count += 1
            logger.warning(f"Deepseek API 请求超时，正在重试 ({retry_count}/{max_retries})...")
            time.sleep(5)  
        
        except Exception as e:
            logger.error(f"调用Deepseek API时发生错误: {str(e)}")
            logger.error(f"错误类型: {type(e)}")
            logger.error(f"错误详情: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"5秒后重试 ({retry_count}/{max_retries})...")
                time.sleep(5)
            else:
                break
    
    logger.warning("无法使用Deepseek API归类热点，将使用原始热点")
    fallback = ""
    for i, item in enumerate(hotspots[:10]):
        try:
            num = str(i + 1).zfill(2)
            source_name = SOURCE_NAME_MAP.get(item.get('source', 'unknown'), item.get('source', 'unknown'))
            item_title = item.get('title', '未知标题')
            
            item_title = item_title.replace('\n', ' ').replace('\r', ' ')
            item_title = ' '.join(item_title.split())
            
            fallback += f"## ** {num} {item_title} **  \n"
            
            item_summary = item.get('summary', '')
            if not item_summary:
                item_summary = f"{item_title}相关信息，详情请查看以下链接。"
            elif len(item_summary) > 100:
                item_summary = item_summary[:97] + "..."
            
            fallback += f"{item_summary}\n\n"
            
            url = item.get('url', '#')
            if not url or url == "#":
                if "Twitter" in source_name:
                    username = source_name.replace("Twitter-", "").strip()
                    username_no_space = username.replace(" ", "")  
                    url = f"https://twitter.com/{username_no_space}"
            
            fallback += f"- [{item_title}]({url}) `🏷️{source_name}` \n\n"
        except Exception as e:
            logger.error(f"处理备选热点时出错(跳过此条): {str(e)}")
            continue
    
    return fallback