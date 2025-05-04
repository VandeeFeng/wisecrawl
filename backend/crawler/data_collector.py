import requests
import cloudscraper
import logging
import feedparser
import time
import os
from datetime import datetime, timedelta, timezone
from config.config import SOURCE_NAME_MAP, XKIT_TWITTER_FEED, XKIT_TWITTER_FEED_URL
from crawler.rss_parser import extract_rss_entry
import json # Ensure json is imported
from bs4 import BeautifulSoup # Import BeautifulSoup
import socket

# Configure logging
logger = logging.getLogger(__name__)

def fetch_hotspot(source, base_url):
    """
    Fetch hotspot data from specified source
    """
    try:
        # Get limit value from environment variable, default is 1
        limit = os.getenv('HOTSPOT_LIMIT', '1')
        url = f"{base_url}/{source}?limit={limit}"
        response = requests.get(url, timeout=10, allow_redirects=True)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 200:
            return data.get("data", [])
        else:
            logger.error(f"Failed to get {source} data: {data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        logger.error(f"Error occurred while getting {source} data: {str(e)}")
        return []

def collect_all_hotspots(sources, base_url):
    """
    Collect hotspot data from all specified sources
    """
    all_hotspots = []
    
    for source in sources:
        logger.info(f"Getting hotspot data from {source}...")
        hotspots = fetch_hotspot(source, base_url)
        
        for item in hotspots:
            # Ensure each hotspot has a title and link
            if "title" in item and "url" in item:
                # Build hotspot data, keep the desc field
                hotspot_data = {
                    "title": item["title"],
                    "url": item["url"],
                    "source": source,
                    "hot": item.get("hot", ""),
                    "time": item.get("time", ""),
                    "timestamp": item.get("timestamp", ""),
                }
                
                # If there's a summary, keep it
                if "desc" in item and item["desc"]:
                    hotspot_data["desc"] = item["desc"]
                    
                all_hotspots.append(hotspot_data)
    
    logger.info(f"Collected a total of {len(all_hotspots)} hotspot data")
    return all_hotspots

def _process_single_rss(feed_url, feed_name, headers, days, cutoff_time, current_time, all_articles):
    """
    Process a single RSS feed and add articles to all_articles list
    Use cloudscraper to try to bypass Cloudflare
    """
    max_retries = 3
    retry_count = 0
    retry_delay = 5
    articles_count = 0
    timeout = 20 # Increase timeout
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting to get RSS feed {feed_name} (using cloudscraper), attempt {retry_count + 1}")

            # Define a common User-Agent
            common_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36' # You can replace with a newer one

            # Create a cloudscraper instance and pass the User-Agent
            scraper = cloudscraper.create_scraper(
                 browser={
                    'browser': 'chrome', # Keep these settings
                    'platform': 'windows',
                    'mobile': False,
                    'custom': common_user_agent # Explicitly set User-Agent
                }
            )

            # Use scraper.get to get the RSS feed
            response = scraper.get(
                feed_url, 
                # headers=headers, # cloudscraper usually manages headers itself, can be commented out or removed
                timeout=timeout,
                allow_redirects=True,
                verify=True
            )
            response.raise_for_status()
            
            # --- Removed Cloudflare manual check code ---
            # content_type = response.headers.get('Content-Type', '')
            # if 'text/html' in content_type and ('cloudflare' in response.text.lower() or 'just a moment' in response.text.lower()):
            #     logger.warning(f"RSS source {feed_name} returned a CloudFlare verification page, unable to get RSS content")
            #     logger.debug(f"CloudFlare page content: {response.text[:200]}...")
            #     raise Exception("Encountered CloudFlare protection, requires browser environment to access")
            # --- End of removal ---
                
            # Parse RSS with the obtained content
            # Note: feedparser needs bytes or str, response.content is bytes
            feed = feedparser.parse(response.content)
            break # Successfully obtained, exit retry loop

        except (requests.exceptions.RequestException, cloudscraper.exceptions.CloudflareException) as e:
             # Check if it's a cloudscraper-specific error that can't be bypassed
            if isinstance(e, cloudscraper.exceptions.CloudflareException) and \
               ("CloudflareJSChallengeError" in str(e) or "CloudflareCaptchaError" in str(e)):
                 logger.warning(f"Cloudscraper failed to bypass Cloudflare protection (RSS): {feed_name}, error: {str(e)}")
                 # Can't bypass Cloudflare protection, don't retry
                 return # Return directly, skip this RSS source

            # Other request errors or retryable Cloudflare errors
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"RSS source {feed_name} access failed: {str(e)}, retrying in {retry_delay} seconds ({retry_count}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                logger.error(f"RSS source {feed_name} access failed, max retries reached: {str(e)}")
                return # Max retries reached, skip this RSS source
        except Exception as e: # Other unknown errors
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Error processing RSS source {feed_name}: {str(e)}, retrying in {retry_delay} seconds ({retry_count}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                logger.error(f"RSS source {feed_name} processing failed, max retries reached: {str(e)}")
                return # Max retries reached, skip this RSS source

    # If the loop ends normally (break), continue processing the feed
    if 'feed' not in locals(): # Ensure feed variable exists (if first attempt failed and no retries)
        logger.error(f"Failed to successfully get and parse RSS source: {feed_name}")
        return
    
    if feed.bozo:  # Check if there are errors in feed parsing
        logger.warning(f"RSS source {feed_name} parse warning: {feed.bozo_exception}")
    
    # Detect if it's Atom format (WeChat official accounts usually use Atom format)
    is_atom_format = False
    if hasattr(feed, 'namespaces') and 'http://www.w3.org/2005/Atom' in feed.namespaces.values():
        is_atom_format = True
        logger.info(f"Detected Atom format RSS source: {feed_name}")
    
    for entry in feed.entries:
        try:
            # Try to get publish time
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_time = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            else:
                # If no time information, assume it's recent
                pub_time = current_time
            
            # Only keep articles from the last 'days' days
            if pub_time >= cutoff_time:
                # Use standardized RSS parsing function to extract information
                entry_data = extract_rss_entry(entry)
                
                # Set different source identifier based on source type
                if feed_name.lower().find('公众号') >= 0:
                    # If it's a WeChat official account type source
                    source = "公众号精选"
                    if entry_data["author"] != "未知作者":
                        source = f"{feed_name}-{entry_data['author']}"
                else:
                    # Other tech blogs or news sources
                    source = feed_name
                
                # Build article data
                article_data = {
                    "title": entry_data["title"],
                    "url": entry_data["link"],
                    "source": source,
                    "hot": "",
                    "time": pub_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp": int(pub_time.timestamp() * 1000),
                    "published": pub_time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # --- Try to get content first ---
                content_found = False
                
                # 1. Check content:encoded
                content_encoded = None
                if hasattr(entry, 'content_encoded'):
                    content_encoded = entry.content_encoded
                elif hasattr(entry, 'get') and entry.get('content_encoded'):
                    content_encoded = entry.get('content_encoded')
                elif hasattr(entry, 'tags') and entry.tags:
                    for tag in entry.tags:
                        if tag.term == 'content_encoded' or tag.get('term') == 'content_encoded':
                            content_encoded = tag.value
                            break
                
                if content_encoded:
                    content_value = content_encoded
                    if isinstance(content_value, str) and content_value.startswith('<![CDATA[') and content_value.endswith(']]>'):
                        content_value = content_value[9:-3]
                    if content_value and len(content_value.strip()) > 20:
                        article_data["content"] = content_value
                        logger.info(f"Got content from content:encoded: {entry_data['title'][:30]}...")
                        content_found = True
                
                # 2. Check content field
                if not content_found and hasattr(entry, 'content') and entry.content:
                    if isinstance(entry.content, list) and len(entry.content) > 0:
                        content_item = entry.content[0]
                        content_value = ""
                        
                        if isinstance(content_item, dict) and 'value' in content_item:
                            content_value = content_item['value']
                        elif hasattr(content_item, 'value'):
                            content_value = content_item.value
                        else:
                            content_value = str(content_item)
                        
                        if content_value and len(content_value.strip()) > 20:
                            article_data["content"] = content_value
                            logger.info(f"Got content from content field: {entry_data['title'][:30]}...")
                            content_found = True
                
                # 3. Check description field
                if not content_found and hasattr(entry, 'description') and entry.description:
                    desc = entry.description
                    if isinstance(desc, str) and desc.startswith('<![CDATA[') and desc.endswith(']]>'):
                        desc = desc[9:-3]
                    if len(desc.strip()) > 20:
                        article_data["content"] = desc
                        logger.info(f"Got content from description field: {entry_data['title'][:30]}...")
                        content_found = True
                
                # --- Get and clean summary (use as desc) ---
                raw_summary = entry_data.get("summary", "")
                cleaned_summary_text = ""
                if raw_summary and isinstance(raw_summary, str):
                    try:
                        soup = BeautifulSoup(raw_summary, 'html.parser')
                        cleaned_summary_text = soup.get_text(strip=True)
                        if len(cleaned_summary_text) > 10 and not cleaned_summary_text.startswith("点击查看原文"):
                            article_data["desc"] = cleaned_summary_text
                            logger.info(f"Got summary from RSS summary: {entry_data['title'][:30]}...")
                    except Exception as parse_err:
                        logger.warning(f"Error parsing summary HTML: {parse_err}")

            all_articles.append(article_data)
            articles_count += 1

        except Exception as entry_err: # Catch errors for this specific entry
            # Log error with entry link if available
            entry_link = "N/A"
            if hasattr(entry, 'link'):
                entry_link = entry.link
            elif hasattr(entry, 'get'):
                entry_link = entry.get('link', 'N/A')

            logger.error(f"Error processing entry from RSS source '{feed_name}': {entry_err}. Entry URL: {entry_link}")
            # Continue to the next entry
            continue

    logger.info(f"Successfully processed {articles_count} articles from RSS source {feed_name} for the last {days} days") # Log count of successfully processed articles


def fetch_rss_articles(rss_url=None, days=1, rss_feeds=None):
    """
    Fetch articles from RSS sources for the specified number of days
    
    Parameters:
        rss_url: Single RSS source URL, if rss_feeds is provided, rss_feeds takes precedence
        days: Number of days to get articles from
        rss_feeds: List of RSS sources, format is [{"name": "source name", "url": "source URL"}, ...]
    """
    # Set request headers to simulate more realistic browser behavior, avoid website blocking and CloudFlare protection mechanisms
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Sec-Ch-Ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.google.com/'
    }
    all_articles = []
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(days=days)
    
    # If rss_feeds list is provided, use it first
    if rss_feeds and isinstance(rss_feeds, list) and len(rss_feeds) > 0:
        logger.info(f"Using RSS feeds list, {len(rss_feeds)} sources in total")
        
        for feed_info in rss_feeds:
            try:
                feed_name = feed_info.get('name', 'Unknown Source')
                
                # Handle Twitter and other multi-account RSS sources
                if feed_name == 'Twitter' and 'accounts' in feed_info:
                    logger.info(f"Processing Twitter multi-account RSS source, {len(feed_info['accounts'])} accounts in total")
                    for account in feed_info['accounts']:
                        account_name = account.get('name', 'Unknown Twitter Account')
                        account_url = account.get('url')
                        
                        if not account_url:
                            logger.warning(f"Twitter account {account_name} did not provide URL, skipping")
                            continue
                            
                        logger.info(f"Getting Twitter account: {account_name} ({account_url})")
                        # Use the same RSS processing logic, but set source to Twitter-account name
                        # Remove self. and set feed_name to more specific account name
                        _process_single_rss(account_url, f"Twitter-{account_name}", headers, days, cutoff_time, current_time, all_articles)
                    
                    # Skip subsequent processing, as we've already processed all Twitter accounts
                    continue
                
                # Process regular RSS source
                feed_url = feed_info.get('url')
                
                if not feed_url:
                    logger.warning(f"RSS source {feed_name} did not provide URL, skipping")
                    continue
                
                logger.info(f"正在获取RSS源: {feed_name} ({feed_url})")
                max_retries = 3
                retry_count = 0
                retry_delay = 5  # 初始重试延迟（秒）
                
                while retry_count < max_retries:
                    try:
                        # 先使用requests获取内容，添加增强的请求头避免被拦截
                        logger.info(f"尝试获取RSS源 {feed_name}，第 {retry_count + 1} 次尝试")
                        session = requests.Session()
                        response = session.get(
                            feed_url, 
                            headers=headers, 
                            timeout=20, 
                            allow_redirects=True,
                            verify=True  # 验证SSL证书
                        )
                        response.raise_for_status()
                        
                        # 检查是否返回了CloudFlare验证页面或其他非RSS内容
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type and ('cloudflare' in response.text.lower() or 'just a moment' in response.text.lower()):
                            logger.warning(f"RSS源 {feed_name} 返回了CloudFlare验证页面，无法获取RSS内容")
                            logger.debug(f"CloudFlare页面内容: {response.text[:200]}...")
                            raise Exception("遇到CloudFlare保护，需要浏览器环境才能访问")
                            
                        # 使用获取到的内容解析RSS
                        feed = feedparser.parse(response.content)
                        break  # 成功获取，跳出重试循环
                        
                    except requests.exceptions.RequestException as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(f"RSS源 {feed_name} 访问失败: {str(e)}，{retry_delay}秒后重试 ({retry_count}/{max_retries})")
                            time.sleep(retry_delay)
                            retry_delay *= 1.5  # 指数退避策略
                        else:
                            logger.error(f"RSS源 {feed_name} 访问失败，已达最大重试次数: {str(e)}")
                            continue  # 继续处理下一个RSS源
                    except Exception as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(f"RSS源 {feed_name} 处理时出错: {str(e)}，{retry_delay}秒后重试 ({retry_count}/{max_retries})")
                            time.sleep(retry_delay)
                            retry_delay *= 1.5  # 指数退避策略
                        else:
                            logger.error(f"RSS源 {feed_name} 处理失败，已达最大重试次数: {str(e)}")
                            continue  # 继续处理下一个RSS源
                
                # 如果达到最大重试次数仍然失败，跳过当前RSS源
                if retry_count >= max_retries:
                    logger.error(f"RSS源 {feed_name} 在 {max_retries} 次尝试后仍然失败，跳过")
                    continue
                
                if feed.bozo:  # 检查feed解析是否有错误
                    logger.warning(f"RSS源 {feed_name} 解析警告: {feed.bozo_exception}")
                
                # 检测是否为Atom格式（微信公众号通常使用Atom格式）
                is_atom_format = False
                if hasattr(feed, 'namespaces') and 'http://www.w3.org/2005/Atom' in feed.namespaces.values():
                    is_atom_format = True
                    logger.info(f"检测到Atom格式的RSS源: {feed_name}")
                
                articles_count = 0
                for entry in feed.entries:
                    try:
                        # 尝试获取发布时间
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            pub_time = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                        else:
                            # 如果没有时间信息，假设是最近的
                            pub_time = current_time
                        
                        # 只保留最近days天的文章
                        if pub_time >= cutoff_time:
                            # 使用标准化的RSS解析函数提取信息
                            entry_data = extract_rss_entry(entry)
                            
                            # 根据源类型设置不同的source标识
                            if feed_name.lower().find('公众号') >= 0:
                                # 如果是公众号类型的源
                                source = "公众号精选"
                                if entry_data["author"] != "未知作者":
                                    source = f"{feed_name}-{entry_data['author']}"
                            else:
                                # 其他技术博客或新闻源
                                source = feed_name
                            
                            # 构建文章数据
                            article_data = {
                                "title": entry_data["title"],
                                "url": entry_data["link"],
                                "source": source,
                                "hot": "",
                                "time": pub_time.strftime("%Y-%m-%d %H:%M:%S"),
                                "timestamp": int(pub_time.timestamp() * 1000),
                                "published": pub_time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # --- 优先尝试获取 content ---
                            content_found = False
                            
                            # 1. 检查 content:encoded
                            content_encoded = None
                            if hasattr(entry, 'content_encoded'):
                                content_encoded = entry.content_encoded
                            elif hasattr(entry, 'get') and entry.get('content_encoded'):
                                content_encoded = entry.get('content_encoded')
                            elif hasattr(entry, 'tags') and entry.tags:
                                for tag in entry.tags:
                                    if tag.term == 'content_encoded' or tag.get('term') == 'content_encoded':
                                        content_encoded = tag.value
                                        break
                            
                            if content_encoded:
                                content_value = content_encoded
                                if isinstance(content_value, str) and content_value.startswith('<![CDATA[') and content_value.endswith(']]>'):
                                    content_value = content_value[9:-3]
                                if content_value and len(content_value.strip()) > 20:
                                    article_data["content"] = content_value
                                    logger.info(f"从 content:encoded 获取到内容: {entry_data['title'][:30]}...")
                                    content_found = True
                            
                            # 2. 检查 content 字段
                            if not content_found and hasattr(entry, 'content') and entry.content:
                                if isinstance(entry.content, list) and len(entry.content) > 0:
                                    content_item = entry.content[0]
                                    content_value = ""
                                    
                                    if isinstance(content_item, dict) and 'value' in content_item:
                                        content_value = content_item['value']
                                    elif hasattr(content_item, 'value'):
                                        content_value = content_item.value
                                    else:
                                        content_value = str(content_item)
                                    
                                    if content_value and len(content_value.strip()) > 20:
                                        article_data["content"] = content_value
                                        logger.info(f"从 content 字段获取到内容: {entry_data['title'][:30]}...")
                                        content_found = True
                            
                            # 3. 检查 description 字段
                            if not content_found and hasattr(entry, 'description') and entry.description:
                                desc = entry.description
                                if isinstance(desc, str) and desc.startswith('<![CDATA[') and desc.endswith(']]>'):
                                    desc = desc[9:-3]
                                if len(desc.strip()) > 20:
                                    article_data["content"] = desc
                                    logger.info(f"从 description 字段获取到内容: {entry_data['title'][:30]}...")
                                    content_found = True
                            
                            # --- 获取并清理 summary (用作 desc) ---
                            raw_summary = entry_data.get("summary", "")
                            cleaned_summary_text = ""
                            if raw_summary and isinstance(raw_summary, str):
                                try:
                                    soup = BeautifulSoup(raw_summary, 'html.parser')
                                    cleaned_summary_text = soup.get_text(strip=True)
                                    if len(cleaned_summary_text) > 10 and not cleaned_summary_text.startswith("点击查看原文"):
                                        article_data["desc"] = cleaned_summary_text
                                        logger.info(f"从 RSS summary 获取到摘要: {entry_data['title'][:30]}...")
                                except Exception as parse_err:
                                    logger.warning(f"解析摘要HTML时出错: {parse_err}")

                        all_articles.append(article_data)
                        articles_count += 1

                    except Exception as entry_err: # Catch errors for this specific entry
                        # Log error with entry link if available
                        entry_link = "N/A"
                        if hasattr(entry, 'link'):
                            entry_link = entry.link
                        elif hasattr(entry, 'get'):
                            entry_link = entry.get('link', 'N/A')

                        logger.error(f"处理 RSS 源 '{feed_name}' 的条目时出错: {entry_err}. Entry URL: {entry_link}")
                        # Continue to the next entry
                        continue

                logger.info(f"从RSS源 {feed_name} 成功处理 {articles_count} 篇最近{days}天的文章") # Log count of successfully processed articles
            except Exception as e:
                 # Log error without assuming 'title' exists in this scope
                logger.error(f"Error processing RSS source {feed_name} ({feed_info.get('url', 'URL N/A')}): {str(e)}")
                # Optionally log traceback for more details
                import traceback
                logger.error(traceback.format_exc()) # Log full traceback for feed-level errors
    
    # If no rss_feeds is provided or rss_feeds is empty, and rss_url is provided, use single rss_url
    elif rss_url:
        try:
            logger.info(f"Using single RSS source: {rss_url}")
            feed_name = "Single RSS Source"
            
            max_retries = 3
            retry_count = 0
            retry_delay = 5  # 初始重试延迟（秒）
            
            while retry_count < max_retries:
                try:
                    # 先使用requests获取内容，添加增强的请求头避免被拦截
                    logger.info(f"尝试获取单个RSS源，第 {retry_count + 1} 次尝试")
                    session = requests.Session()
                    response = session.get(
                        rss_url, 
                        headers=headers, 
                        timeout=20, 
                        allow_redirects=True,
                        verify=True  # 验证SSL证书
                    )
                    response.raise_for_status()
                    
                    # 检查是否返回了CloudFlare验证页面或其他非RSS内容
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type and ('cloudflare' in response.text.lower() or 'just a moment' in response.text.lower()):
                        logger.warning(f"RSS源返回了CloudFlare验证页面，无法获取RSS内容")
                        logger.debug(f"CloudFlare页面内容: {response.text[:200]}...")
                        raise Exception("遇到CloudFlare保护，需要浏览器环境才能访问")
                    
                    # 使用获取到的内容解析RSS
                    feed = feedparser.parse(response.content)
                    break  # 成功获取，跳出重试循环
                    
                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"RSS源访问失败: {str(e)}，{retry_delay}秒后重试 ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5  # 指数退避策略
                    else:
                        logger.error(f"RSS源访问失败，已达最大重试次数: {str(e)}")
                        return []
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"RSS源处理时出错: {str(e)}，{retry_delay}秒后重试 ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5  # 指数退避策略
                    else:
                        logger.error(f"RSS源处理失败，已达最大重试次数: {str(e)}")
                        return []
            
            # 如果达到最大重试次数仍然失败，返回空列表
            if retry_count >= max_retries:
                logger.error(f"RSS源在 {max_retries} 次尝试后仍然失败")
                return []
            
            if feed.bozo:  # 检查feed解析是否有错误
                logger.warning(f"RSS解析警告: {feed.bozo_exception}")
            
            # 检测是否为Atom格式（微信公众号通常使用Atom格式）
            is_atom_format = False
            if hasattr(feed, 'namespaces') and 'http://www.w3.org/2005/Atom' in feed.namespaces.values():
                is_atom_format = True
                logger.info(f"检测到Atom格式的RSS源")
            
            articles_count = 0
            for entry in feed.entries:
                try:
                    # 尝试获取发布时间
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_time = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                    else:
                        # 如果没有时间信息，假设是最近的
                        pub_time = current_time
                    
                    # 只保留最近days天的文章
                    if pub_time >= cutoff_time:
                        # 使用标准化的RSS解析函数提取信息
                        entry_data = extract_rss_entry(entry)
                        
                        # 根据源类型设置不同的source标识
                        if feed_name.lower().find('公众号') >= 0:
                            # 如果是公众号类型的源
                            source = "公众号精选"
                            if entry_data["author"] != "未知作者":
                                source = f"{feed_name}-{entry_data['author']}"
                        else:
                            # 其他技术博客或新闻源
                            source = feed_name
                        
                        # 构建文章数据
                        article_data = {
                            "title": entry_data["title"],
                            "url": entry_data["link"],
                            "source": source,
                            "hot": "",
                            "time": pub_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "timestamp": int(pub_time.timestamp() * 1000),
                            "published": pub_time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # --- 优先尝试获取 content ---
                        content_found = False
                        
                        # 1. 检查 content:encoded
                        content_encoded = None
                        if hasattr(entry, 'content_encoded'):
                            content_encoded = entry.content_encoded
                        elif hasattr(entry, 'get') and entry.get('content_encoded'):
                            content_encoded = entry.get('content_encoded')
                        elif hasattr(entry, 'tags') and entry.tags:
                            for tag in entry.tags:
                                if tag.term == 'content_encoded' or tag.get('term') == 'content_encoded':
                                    content_encoded = tag.value
                                    break
                        
                        if content_encoded:
                            content_value = content_encoded
                            if isinstance(content_value, str) and content_value.startswith('<![CDATA[') and content_value.endswith(']]>'):
                                content_value = content_value[9:-3]
                            if content_value and len(content_value.strip()) > 20:
                                article_data["content"] = content_value
                                logger.info(f"从 content:encoded 获取到内容: {entry_data['title'][:30]}...")
                                content_found = True
                        
                        # 2. 检查 content 字段
                        if not content_found and hasattr(entry, 'content') and entry.content:
                            if isinstance(entry.content, list) and len(entry.content) > 0:
                                content_item = entry.content[0]
                                content_value = ""
                                
                                if isinstance(content_item, dict) and 'value' in content_item:
                                    content_value = content_item['value']
                                elif hasattr(content_item, 'value'):
                                    content_value = content_item.value
                                else:
                                    content_value = str(content_item)
                                
                                if content_value and len(content_value.strip()) > 20:
                                    article_data["content"] = content_value
                                    logger.info(f"从 content 字段获取到内容: {entry_data['title'][:30]}...")
                                    content_found = True
                        
                        # 3. 检查 description 字段
                        if not content_found and hasattr(entry, 'description') and entry.description:
                            desc = entry.description
                            if isinstance(desc, str) and desc.startswith('<![CDATA[') and desc.endswith(']]>'):
                                desc = desc[9:-3]
                            if len(desc.strip()) > 20:
                                article_data["content"] = desc
                                logger.info(f"从 description 字段获取到内容: {entry_data['title'][:30]}...")
                                content_found = True
                        
                        # --- 获取并清理 summary (用作 desc) ---
                        raw_summary = entry_data.get("summary", "")
                        cleaned_summary_text = ""
                        if raw_summary and isinstance(raw_summary, str):
                            try:
                                soup = BeautifulSoup(raw_summary, 'html.parser')
                                cleaned_summary_text = soup.get_text(strip=True)
                                if len(cleaned_summary_text) > 10 and not cleaned_summary_text.startswith("点击查看原文"):
                                    article_data["desc"] = cleaned_summary_text
                                    logger.info(f"从 RSS summary 获取到摘要: {entry_data['title'][:30]}...")
                            except Exception as parse_err:
                                logger.warning(f"解析摘要HTML时出错: {parse_err}")

                        all_articles.append(article_data)
                        articles_count += 1

                except Exception as entry_err: # Catch errors for this specific entry
                    entry_link = "N/A"
                    if hasattr(entry, 'link'):
                        entry_link = entry.link
                    elif hasattr(entry, 'get'):
                        entry_link = entry.get('link', 'N/A')
                    # Try to get feed_url for context, assuming rss_url is available in this scope
                    feed_url_context = rss_url if 'rss_url' in locals() else "URL N/A" 
                    logger.error(f"处理单个 RSS 源 '{feed_url_context}' 的条目时出错: {entry_err}. Entry URL: {entry_link}")
                    # Continue to the next entry
                    continue

            logger.info(f"从单个RSS源 {rss_url} 成功处理 {articles_count} 篇最近{days}天的文章") # Log successful count
        except Exception as e:
            logger.error(f"处理单个 RSS 源 {rss_url} 时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc()) # Log full traceback

    else:
        logger.warning("No RSS source provided, cannot get articles")
    
    logger.info(f"Got a total of {len(all_articles)} articles from all RSS sources for the last {days} days")
    return all_articles

def filter_recent_hotspots(hotspots, days=1):
    """
    Filter hotspot data within the time range
    Time range: All of yesterday + today until current time
    """
    filtered_hotspots = []
    current_time = datetime.now()
    
    # Set time range: yesterday at 00:00 until now
    yesterday = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    
    logger.info(f"Current time: {current_time}, filter time range: {yesterday} to {current_time}")
    
    for item in hotspots:
        # Try to parse timestamp
        timestamp = item.get("timestamp") or item.get("time", "")
        
        if timestamp:
            try:
                # Convert timestamp to datetime object
                if isinstance(timestamp, str):
                    if 'T' in timestamp and ('Z' in timestamp or '+' in timestamp):
                        # ISO format: 2025-03-08T12:04:22.020Z
                        item_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        # Try to process as number
                        timestamp = float(timestamp)
                        # Convert millisecond timestamp to second timestamp
                        if timestamp > 9999999999:
                            timestamp = timestamp / 1000
                        item_time = datetime.fromtimestamp(timestamp)
                else:
                    # Numeric timestamp
                    if timestamp > 9999999999:  # Millisecond timestamp
                        timestamp = timestamp / 1000
                    item_time = datetime.fromtimestamp(float(timestamp))
                
                # Check if time is in the future (possibly an incorrect timestamp)
                if item_time > current_time + timedelta(hours=1):
                    # Could be a future timestamp, try to adjust the year
                    logger.warning(f"Detected future timestamp: {item_time}, title: {item['title']}")
                    
                    # If the timestamp year is a future year, adjust to current year
                    if item_time.year > current_time.year:
                        adjusted_year = current_time.year
                        try:
                            item_time = item_time.replace(year=adjusted_year)
                            logger.info(f"Adjusted timestamp year to current year: {item_time}")
                        except ValueError as e:
                            logger.warning(f"Failed to adjust timestamp year: {str(e)}")
                
                # Log the parse result
                logger.info(f"Hotspot: {item['title'][:30]}..., time: {item_time}")
                
                # Only keep hotspots from yesterday at 00:00 until now
                if yesterday <= item_time <= current_time:
                    filtered_hotspots.append(item)
                    continue
                else:
                    logger.info(f"Discarded hotspot outside time range: {item['title']}, time: {item_time}")
                    continue
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse timestamp: {timestamp}, error: {str(e)}, title: {item['title']}")
        
        # If no valid timestamp or parsing failed, keep the item by default
        logger.info(f"No valid timestamp, keeping by default: {item['title']}")
        filtered_hotspots.append(item)
    
    logger.info(f"Kept {len(filtered_hotspots)}/{len(hotspots)} hotspots after time range filtering")
    return filtered_hotspots

def fetch_twitter_feed(days_to_fetch=2):
    """
    Get tweet JSON data from GitHub Raw URL for the last few days and format it.
    If XKIT_TWITTER_FEED is set to False in config, will return empty list.

    Parameters:
        days_to_fetch (int): How many days of data to fetch, default is 2 days.

    Returns:
        list: List of formatted tweet data, format same as hotspot_data.
    """
    # Check if Twitter feed is enabled in config
    if not XKIT_TWITTER_FEED:
        logger.info("Xkit Twitter feed is disabled in configuration, skipping.")
        return []
        
    all_tweets_formatted = []
    base_url = XKIT_TWITTER_FEED_URL
    today = datetime.now()

    logger.info(f"Starting to fetch Twitter Feed for the last {days_to_fetch} days...")

    for i in range(days_to_fetch):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        file_url = f"{base_url}{date_str}.json"
        logger.info(f"Trying to get tweet file: {file_url}")

        try:
            # Use requests to get JSON file, GitHub Raw generally doesn't need cloudscraper
            response = requests.get(file_url, timeout=15)

            # Check if successfully obtained
            if response.status_code == 404:
                logger.warning(f"Tweet file for {date_str} not found, skipping: {file_url}")
                continue
            response.raise_for_status() # Check other HTTP errors

            # Parse JSON data
            tweets_data = response.json()

            if not isinstance(tweets_data, list):
                 logger.warning(f"Tweet data format is not a list, skipping: {file_url}")
                 continue

            logger.info(f"Successfully got and parsed tweets for {date_str}, {len(tweets_data)} tweets in total")

            # Format tweet data
            for tweet in tweets_data:
                try:
                    # Parse creation time
                    # Format: Sat Mar 29 07:42:16 +0000 2025
                    created_at_str = tweet.get("createdAt")
                    created_at_dt = None
                    timestamp_ms = None
                    published_str = ""
                    if created_at_str:
                        try:
                            # Python 3.7+ supports %z to parse +0000
                            created_at_dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
                            timestamp_ms = int(created_at_dt.timestamp() * 1000)
                            published_str = created_at_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except ValueError as time_err:
                            logger.warning(f"Failed to parse tweet time: {created_at_str}, error: {time_err}")
                            # If parsing fails, can try other formats or skip timestamp

                    # Build title (take first 47 characters of fullText + ...)
                    full_text = tweet.get("fullText", "")
                    if len(full_text) > 50:
                        title = full_text[:47] + "..."
                    else:
                        title = full_text # Use full text if shorter than 50

                    # Get source
                    source_name = "Twitter"
                    user_info = tweet.get("user")
                    if user_info:
                        display_name = user_info.get("name")
                        screen_name = user_info.get("screenName")
                        if display_name: # Prefer display name
                            source_name = f"Twitter-{display_name}"
                        elif screen_name: # If no display name, use screenName
                            source_name = f"Twitter-{screen_name}"
                        # If neither is available, keep "Twitter"

                    # Format as standard dictionary
                    formatted_tweet = {
                        "title": title,
                        "url": tweet.get("tweetUrl", ""),
                        "source": source_name,
                        "content": tweet.get("fullText", ""), # Use fullText as content
                        "hot": "", # Tweets don't have a hot value
                        "time": published_str, # Use formatted time string
                        "timestamp": timestamp_ms, # Use millisecond timestamp
                        "published": published_str, # Add published field again to be compatible with RSS format
                        "desc": full_text, # Use full tweet text as initial description
                    }
                    # Tweets don't have a preset summary, so desc field is not added

                    all_tweets_formatted.append(formatted_tweet)

                except Exception as format_err:
                    logger.error(f"Error formatting tweet: {format_err}, tweet URL: {tweet.get('tweetUrl')}")

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Failed to get tweet file: {file_url}, error: {req_err}")
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to parse tweet JSON: {file_url}, error: {json_err}")
        except Exception as e:
            logger.error(f"Unknown error while processing tweet file: {file_url}, error: {e}")

    logger.info(f"Got and formatted a total of {len(all_tweets_formatted)} tweets")
    return all_tweets_formatted