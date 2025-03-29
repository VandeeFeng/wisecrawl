#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻数据收集：收集hotnews和公众号文章
"""

import requests
import cloudscraper
import logging
import feedparser
import time
import os
from datetime import datetime, timedelta, timezone
from config.config import SOURCE_NAME_MAP
from crawler.rss_parser import extract_rss_entry
import json # 确保导入 json
from bs4 import BeautifulSoup # 导入 BeautifulSoup
import socket

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

def _process_single_rss(feed_url, feed_name, headers, days, cutoff_time, current_time, all_articles):
    """
    处理单个RSS源并将文章添加到all_articles列表中
    使用 cloudscraper 尝试绕过 Cloudflare
    """
    max_retries = 3
    retry_count = 0
    retry_delay = 5
    articles_count = 0
    timeout = 20 # 增加超时时间
    
    while retry_count < max_retries:
        try:
            logger.info(f"尝试获取RSS源 {feed_name} (使用 cloudscraper)，第 {retry_count + 1} 次尝试")

            # 定义一个常见的 User-Agent
            common_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36' # 你可以替换成更新的

            # 创建 cloudscraper 实例，并传入 User-Agent
            scraper = cloudscraper.create_scraper(
                 browser={
                    'browser': 'chrome', # 保持这些设置
                    'platform': 'windows',
                    'mobile': False,
                    'custom': common_user_agent # 显式设置 User-Agent
                }
            )

            # 使用 scraper.get 获取 RSS feed
            response = scraper.get(
                feed_url, 
                # headers=headers, # cloudscraper 通常自己管理头，可以注释掉或移除
                timeout=timeout,
                allow_redirects=True,
                verify=True
            )
            response.raise_for_status()
            
            # --- 移除 Cloudflare 手动检查代码 ---
            # content_type = response.headers.get('Content-Type', '')
            # if 'text/html' in content_type and ('cloudflare' in response.text.lower() or 'just a moment' in response.text.lower()):
            #     logger.warning(f"RSS源 {feed_name} 返回了CloudFlare验证页面，无法获取RSS内容")
            #     logger.debug(f"CloudFlare页面内容: {response.text[:200]}...")
            #     raise Exception("遇到CloudFlare保护，需要浏览器环境才能访问")
            # --- 移除结束 ---
                
            # 使用获取到的内容解析RSS
            # 注意：feedparser 需要 bytes 或 str，response.content 是 bytes
            feed = feedparser.parse(response.content)
            break # 成功获取，跳出重试循环

        except (requests.exceptions.RequestException, cloudscraper.exceptions.CloudflareException) as e:
             # 检查是否是 cloudscraper 特有的无法绕过的错误
            if isinstance(e, cloudscraper.exceptions.CloudflareException) and \
               ("CloudflareJSChallengeError" in str(e) or "CloudflareCaptchaError" in str(e)):
                 logger.warning(f"Cloudscraper 未能绕过 Cloudflare 保护 (RSS): {feed_name}, 错误: {str(e)}")
                 # 遇到无法绕过的 Cloudflare 保护，不再重试
                 return # 直接返回，跳过此RSS源

            # 其他请求错误或可重试的 Cloudflare 错误
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"RSS源 {feed_name} 访问失败: {str(e)}，{retry_delay}秒后重试 ({retry_count}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                logger.error(f"RSS源 {feed_name} 访问失败，已达最大重试次数: {str(e)}")
                return # 达到最大重试次数，跳过此RSS源
        except Exception as e: # 其他未知错误
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"RSS源 {feed_name} 处理时出错: {str(e)}，{retry_delay}秒后重试 ({retry_count}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                logger.error(f"RSS源 {feed_name} 处理失败，已达最大重试次数: {str(e)}")
                return # 达到最大重试次数，跳过此RSS源

    # 如果循环正常结束（break），则继续处理 feed
    if 'feed' not in locals(): # 确保 feed 变量存在 (如果第一次尝试就失败且没重试)
        logger.error(f"未能成功获取并解析 RSS 源: {feed_name}")
        return
    
    if feed.bozo:  # 检查feed解析是否有错误
        logger.warning(f"RSS源 {feed_name} 解析警告: {feed.bozo_exception}")
    
    # 检测是否为Atom格式（微信公众号通常使用Atom格式）
    is_atom_format = False
    if hasattr(feed, 'namespaces') and 'http://www.w3.org/2005/Atom' in feed.namespaces.values():
        is_atom_format = True
        logger.info(f"检测到Atom格式的RSS源: {feed_name}")
    
    for entry in feed.entries:
        try: # Add try block for individual entry processing
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
                articles_count += 1
                entry_data = extract_rss_entry(entry)
                
                # 根据源类型设置不同的source标识
                if feed_name.lower().find('公众号') >= 0 or is_atom_format:
                    # 如果是公众号类型的源或Atom格式
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
                    "published": entry_data["published"] or pub_time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 检查是否已有内容或摘要，如果有则直接添加，避免后续重复爬取
                content_found = False
                
                # 首先检查content:encoded字段（WordPress和一些RSS 2.0格式常用）
                # 尝试多种可能的方式获取content:encoded字段
                content_encoded = None
                
                # 方法1: 直接作为属性
                if hasattr(entry, 'content_encoded'):
                    content_encoded = entry.content_encoded
                # 方法2: 作为字典项
                elif hasattr(entry, 'get') and entry.get('content_encoded'):
                    content_encoded = entry.get('content_encoded')
                # 方法3: 通过命名空间查找
                elif hasattr(entry, 'tags') and entry.tags:
                    for tag in entry.tags:
                        if tag.term == 'content_encoded' or tag.get('term') == 'content_encoded':
                            content_encoded = tag.value
                            break
                # 方法4: 通过feedparser的命名空间处理方式
                # 在RSS 2.0中，content:encoded通常是通过命名空间定义的
                # feedparser会将命名空间标签转换为特定格式：{命名空间前缀}_{标签名}
                elif hasattr(entry, 'content_encoded') or hasattr(entry, 'content:encoded'):
                    content_encoded = getattr(entry, 'content_encoded', None) or getattr(entry, 'content:encoded', None)
                # 方法5: 检查是否有content命名空间的属性
                elif hasattr(feed, 'namespaces') and 'http://purl.org/rss/1.0/modules/content/' in feed.namespaces.values():
                    # 找出content命名空间的前缀
                    content_prefix = None
                    for prefix, uri in feed.namespaces.items():
                        if uri == 'http://purl.org/rss/1.0/modules/content/':
                            content_prefix = prefix
                            break
                    
                    if content_prefix:
                        # 构造可能的属性名
                        possible_attr = f"{content_prefix}_encoded"
                        if hasattr(entry, possible_attr):
                            content_encoded = getattr(entry, possible_attr)
                            logger.info(f"通过命名空间前缀找到content:encoded字段: {possible_attr}")
                
                # 方法6: 检查是否有content命名空间的其他可能属性名
                if not content_encoded and hasattr(feed, 'namespaces'):
                    for prefix, uri in feed.namespaces.items():
                        if 'content' in uri.lower():
                            # 尝试不同的组合方式
                            possible_attrs = [
                                f"{prefix}_encoded",
                                f"{prefix}encoded",
                                f"content_{prefix}",
                                f"content{prefix}"
                            ]
                            for attr in possible_attrs:
                                if hasattr(entry, attr):
                                    content_encoded = getattr(entry, attr)
                                    logger.info(f"通过命名空间组合找到content:encoded字段: {attr}")
                                    break
                            if content_encoded:
                                break
                
                # 方法7: 尝试查找所有可能的属性名
                if not content_encoded:
                    # 遍历entry的所有属性，查找可能包含content:encoded的属性
                    for attr_name in dir(entry):
                        if 'content' in attr_name.lower() and 'encoded' in attr_name.lower():
                            content_value_attr = getattr(entry, attr_name)
                            # Check if the attribute value is a string and has content
                            if isinstance(content_value_attr, str):
                                # Handle CDATA if present
                                if content_value_attr.startswith('<![CDATA[') and content_value_attr.endswith(']]>'):
                                    content_value_attr = content_value_attr[9:-3]
                                if content_value_attr and len(content_value_attr.strip()) > 20:
                                    content_encoded = content_value_attr # Assign to content_encoded if valid
                                    logger.info(f"找到可能的content:encoded字段: {attr_name}")
                                    break # Found a potential content, stop searching

                if content_encoded:
                    content_value = content_encoded # Now use content_encoded safely
                    # 处理CDATA标签 (Redundant check, handled above, but keep for safety)
                    if isinstance(content_value, str) and content_value.startswith('<![CDATA[') and content_value.endswith(']]>'):
                        content_value = content_value[9:-3]  # 去除CDATA标签

                    if content_value and len(content_value.strip()) > 20:
                        article_data["content"] = content_value
                        logger.info(f"从RSS源的content:encoded字段获取到内容: {entry_data['title'][:30]}...")
                        content_found = True
                    else:
                        logger.info(f"RSS源的content:encoded字段存在但内容为空或不足: {entry_data['title'][:30]}...")
                        # 尝试从entry的原始属性中查找
                        if hasattr(entry, '__dict__'):
                            for key, value in entry.__dict__.items():
                                if 'content' in key.lower() and isinstance(value, str) and len(value.strip()) > 20:
                                    logger.info(f"从entry.__dict__中找到可能的内容字段: {key}")
                                    article_data["content"] = value
                                    content_found = True
                                    break

                # 尝试从原始XML中提取内容
                if not content_found and hasattr(feed, 'feed') and hasattr(feed.feed, 'links'):
                    try:
                        # 检查是否有原始XML
                        if hasattr(entry, 'xml') and entry.xml:
                            import re
                            # 尝试使用正则表达式提取content:encoded内容
                            content_match = re.search(r'<content:encoded><!\[CDATA\[(.*?)\]\]></content:encoded>', 
                                                    entry.xml, re.DOTALL)
                            if content_match:
                                content_value = content_match.group(1)
                                if content_value and len(content_value.strip()) > 20:
                                    article_data["content"] = content_value
                                    logger.info(f"从XML原始数据中提取到content:encoded内容: {entry_data['title'][:30]}...")
                                    content_found = True
                    except Exception as e:
                        logger.warning(f"尝试从XML提取内容时出错: {str(e)}")
                
                # 如果是机器之心的RSS源，尝试特殊处理
                if not content_found and hasattr(feed, 'href') and feed.href and 'jiqizhixin' in feed.href.lower():
                    logger.info(f"检测到机器之心RSS源，尝试特殊处理: {entry_data['title'][:30]}...")
                    # 尝试从description字段获取内容
                    if hasattr(entry, 'description') and entry.description:
                        desc = entry.description
                        if isinstance(desc, str) and desc.startswith('<![CDATA[') and desc.endswith(']]>'):
                            desc = desc[9:-3]  # 去除CDATA标签
                        if len(desc.strip()) > 20:
                            article_data["content"] = desc
                            logger.info(f"从机器之心RSS源的description字段获取到内容: {entry_data['title'][:30]}...")
                            content_found = True
                
                # 如果content:encoded没有内容，再检查content字段
                if not content_found and hasattr(entry, 'content') and entry.content:
                    # 有些RSS源会在content字段提供完整内容
                    if isinstance(entry.content, list) and len(entry.content) > 0:
                        content_item = entry.content[0]
                        content_value = ""
                        
                        # 处理不同格式的content
                        if isinstance(content_item, dict) and 'value' in content_item:
                            content_value = content_item.value
                        elif hasattr(content_item, 'value'):
                            content_value = content_item.value
                        else:
                            content_value = str(content_item)
                        
                        # 检查content_value是否为空字符串或只包含空白字符
                        if content_value and len(content_value.strip()) > 20:
                            article_data["content"] = content_value
                            logger.info(f"从RSS源直接获取到内容: {entry_data['title'][:30]}...")
                            content_found = True
                        else:
                            logger.info(f"RSS源的content字段为空或内容不足: {entry_data['title'][:30]}...")
                
                # 检查是否有摘要
                if hasattr(entry, 'summary') and entry.summary:
                    summary = entry.summary
                    # 处理不同格式的summary
                    if isinstance(summary, dict) and 'value' in summary:
                        summary = summary.value
                    
                    if summary and isinstance(summary, str) and len(summary.strip()) > 20:  # Ensure summary has content
                        article_data["desc"] = summary
                        logger.info(f"从RSS源直接获取到摘要: {entry_data['title'][:30]}...")
            
            all_articles.append(article_data)
            articles_count += 1 # Increment counter only for successfully processed articles

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


def fetch_rss_articles(rss_url=None, days=1, rss_feeds=None):
    """
    从RSS源获取最近指定天数内的文章
    
    参数:
        rss_url: 单个RSS源URL，如果提供rss_feeds则优先使用rss_feeds
        days: 获取最近几天的文章
        rss_feeds: RSS源列表，格式为[{"name": "源名称", "url": "源URL"}, ...]
    """
    # 设置请求头，模拟更真实的浏览器行为，避免被网站拦截和CloudFlare保护机制
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
    
    # 如果提供了rss_feeds列表，优先使用它
    if rss_feeds and isinstance(rss_feeds, list) and len(rss_feeds) > 0:
        logger.info(f"使用RSS源列表，共{len(rss_feeds)}个源")
        
        for feed_info in rss_feeds:
            try:
                feed_name = feed_info.get('name', '未知来源')
                
                # 处理Twitter等多账号RSS源
                if feed_name == 'Twitter' and 'accounts' in feed_info:
                    logger.info(f"处理Twitter多账号RSS源，共{len(feed_info['accounts'])}个账号")
                    for account in feed_info['accounts']:
                        account_name = account.get('name', '未知Twitter账号')
                        account_url = account.get('url')
                        
                        if not account_url:
                            logger.warning(f"Twitter账号 {account_name} 未提供URL，跳过")
                            continue
                            
                        logger.info(f"正在获取Twitter账号: {account_name} ({account_url})")
                        # 使用相同的RSS处理逻辑，但将source设置为Twitter-账号名
                        # 移除 self. 并将 feed_name 设为更具体的账号名
                        _process_single_rss(account_url, f"Twitter-{account_name}", headers, days, cutoff_time, current_time, all_articles)
                    
                    # 跳过后续处理，因为已经处理了所有Twitter账号
                    continue
                
                # 处理常规RSS源
                feed_url = feed_info.get('url')
                
                if not feed_url:
                    logger.warning(f"RSS源 {feed_name} 未提供URL，跳过")
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
                    try: # Add try block for individual entry processing
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
                            articles_count += 1
                            entry_data = extract_rss_entry(entry)
                            
                            # 根据源类型设置不同的source标识
                            if feed_name.lower().find('公众号') >= 0 or is_atom_format:
                                # 如果是公众号类型的源或Atom格式
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
                                "published": entry_data["published"] or pub_time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            content_found = False
                            # --- 优先尝试获取 content --- 
                            # 1. 从 entry_data 获取预解析的 content (如果有)
                            if entry_data.get("content"):
                                content_value = entry_data["content"]
                                # 基本清理 (去除CDATA)
                                if isinstance(content_value, str) and content_value.startswith('<![CDATA[') and content_value.endswith(']]>'):
                                    content_value = content_value[9:-3]
                                if content_value and len(content_value.strip()) > 20:
                                    article_data["content"] = content_value
                                    logger.info(f"从 entry_data 获取到 content: {entry_data['title'][:30]}...")
                                    content_found = True
                            
                            # 2. 检查 content:encoded (如果上面没找到)
                            if not content_found:
                                # ... (Existing complex logic for finding content_encoded, using BeautifulSoup might simplify this)
                                # Example simplification: Let BeautifulSoup handle finding content-like tags
                                potential_content_html = ""
                                if hasattr(entry, 'content_encoded'): potential_content_html = entry.content_encoded
                                elif hasattr(entry, 'content'): # Check standard content field too
                                    if isinstance(entry.content, list) and entry.content:
                                        cont = entry.content[0]
                                        if isinstance(cont, dict) and 'value' in cont: potential_content_html = cont.value
                                        elif hasattr(cont, 'value'): potential_content_html = cont.value
                                        else: potential_content_html = str(cont)
                                
                                if potential_content_html and isinstance(potential_content_html, str):
                                    # Basic clean (CDATA)
                                    if potential_content_html.startswith('<![CDATA[') and potential_content_html.endswith(']]>'):
                                        potential_content_html = potential_content_html[9:-3]
                                    # Use BeautifulSoup to get cleaner text if needed, or store raw HTML if long enough
                                    if len(potential_content_html.strip()) > 100: # Heuristic for actual content vs short descriptions
                                        article_data["content"] = potential_content_html
                                        logger.info(f"从 RSS content/content_encoded 获取到较长内容: {entry_data['title'][:30]}...")
                                        content_found = True

                            # --- 获取并清理 summary (用作 desc) --- 
                            raw_summary = entry_data.get("summary", "")
                            cleaned_summary_text = ""
                            is_summary_valid = False # Flag to track validity
                            if raw_summary and isinstance(raw_summary, str):
                                try:
                                    # 使用BeautifulSoup去除HTML标签
                                    soup = BeautifulSoup(raw_summary, 'html.parser')
                                    cleaned_summary_text = soup.get_text(strip=True)
                                except Exception as parse_err:
                                    logger.warning(f"解析摘要HTML时出错 for {entry_data['title'][:30]}: {parse_err}. 使用原始摘要.")
                                    # cleaned_summary_text = raw_summary # Fallback removed, prefer AI summary if parsing fails

                            # 检查清理后的文本是否有效 (不太短, 不像链接)
                            MIN_DESC_LENGTH = 10
                            if cleaned_summary_text and \
                                len(cleaned_summary_text) > MIN_DESC_LENGTH and \
                                not cleaned_summary_text.startswith("点击查看原文") and \
                                "href=" not in cleaned_summary_text[:20]: # Added heuristic check for links

                                article_data["desc"] = cleaned_summary_text
                                is_summary_valid = True
                                logger.info(f"从 RSS summary 获取到有效 desc (可能较长, len={len(cleaned_summary_text)}): {entry_data['title'][:30]}...")
                            
                            # Log reason for invalidity if parsing succeeded but checks failed
                            if not is_summary_valid and cleaned_summary_text:
                                if len(cleaned_summary_text) <= MIN_DESC_LENGTH:
                                    reason = "太短"
                                elif cleaned_summary_text.startswith("点击查看原文") or "href=" in cleaned_summary_text[:20]:
                                    reason = "像链接或固定文本"
                                else: # Ensure this else aligns correctly
                                    reason = "未知原因(非太短/非链接)" # More specific reason
                                logger.info(f"RSS summary 无效 ({reason})，将不使用: '{cleaned_summary_text[:50]}...' for {entry_data['title'][:30]}")
                            elif not is_summary_valid and not cleaned_summary_text: # Align elif correctly
                                logger.info(f"RSS summary 为空或解析失败 for {entry_data['title'][:30]}")
                            
                            all_articles.append(article_data)
                            articles_count += 1 # Increment counter only for successfully processed articles

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
                logger.error(f"处理 RSS 源 {feed_name} ({feed_info.get('url', 'URL N/A')}) 时发生错误: {str(e)}")
                # Optionally log traceback for more details
                import traceback
                logger.error(traceback.format_exc()) # Log full traceback for feed-level errors
    
    # 如果没有提供rss_feeds或rss_feeds为空，且提供了rss_url，则使用单个rss_url
    elif rss_url:
        try:
            logger.info(f"使用单个RSS源: {rss_url}")
            
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
            
            articles_count = 0 # Initialize counter
            for entry in feed.entries:
                try: # Add try block for individual entry processing
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
                        articles_count += 1
                        entry_data = extract_rss_entry(entry)
                        
                        # 根据源类型设置不同的source标识
                        if feed_name.lower().find('公众号') >= 0 or is_atom_format:
                            # 如果是公众号类型的源或Atom格式
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
                            "published": entry_data["published"] or pub_time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        content_found = False
                        # --- 优先尝试获取 content --- 
                        # 1. 从 entry_data 获取预解析的 content (如果有)
                        if entry_data.get("content"):
                            content_value = entry_data["content"]
                            # 基本清理 (去除CDATA)
                            if isinstance(content_value, str) and content_value.startswith('<![CDATA[') and content_value.endswith(']]>'):
                                content_value = content_value[9:-3]
                            if content_value and len(content_value.strip()) > 20:
                                article_data["content"] = content_value
                                logger.info(f"从 entry_data 获取到 content: {entry_data['title'][:30]}...")
                                content_found = True
                        
                        # 2. 检查 content:encoded (如果上面没找到)
                        if not content_found:
                            # ... (Existing complex logic for finding content_encoded, using BeautifulSoup might simplify this)
                            # Example simplification: Let BeautifulSoup handle finding content-like tags
                            potential_content_html = ""
                            if hasattr(entry, 'content_encoded'): potential_content_html = entry.content_encoded
                            elif hasattr(entry, 'content'): # Check standard content field too
                                if isinstance(entry.content, list) and entry.content:
                                    cont = entry.content[0]
                                    if isinstance(cont, dict) and 'value' in cont: potential_content_html = cont.value
                                    elif hasattr(cont, 'value'): potential_content_html = cont.value
                                    else: potential_content_html = str(cont)
                            
                            if potential_content_html and isinstance(potential_content_html, str):
                                # Basic clean (CDATA)
                                if potential_content_html.startswith('<![CDATA[') and potential_content_html.endswith(']]>'):
                                    potential_content_html = potential_content_html[9:-3]
                                # Use BeautifulSoup to get cleaner text if needed, or store raw HTML if long enough
                                if len(potential_content_html.strip()) > 100: # Heuristic for actual content vs short descriptions
                                    article_data["content"] = potential_content_html
                                    logger.info(f"从 RSS content/content_encoded 获取到较长内容: {entry_data['title'][:30]}...")
                                    content_found = True

                        # --- 获取并清理 summary (用作 desc) --- 
                        raw_summary = entry_data.get("summary", "")
                        cleaned_summary_text = ""
                        is_summary_valid = False # Flag to track validity
                        if raw_summary and isinstance(raw_summary, str):
                            try:
                                # 使用BeautifulSoup去除HTML标签
                                soup = BeautifulSoup(raw_summary, 'html.parser')
                                cleaned_summary_text = soup.get_text(strip=True)
                            except Exception as parse_err:
                                logger.warning(f"解析摘要HTML时出错 for {entry_data['title'][:30]}: {parse_err}. 使用原始摘要.")
                                # cleaned_summary_text = raw_summary # Fallback removed, prefer AI summary if parsing fails

                        # 检查清理后的文本是否有效 (不太短, 不像链接)
                        MIN_DESC_LENGTH = 10
                        if cleaned_summary_text and \
                            len(cleaned_summary_text) > MIN_DESC_LENGTH and \
                            not cleaned_summary_text.startswith("点击查看原文") and \
                            "href=" not in cleaned_summary_text[:20]: # Added heuristic check for links

                            article_data["desc"] = cleaned_summary_text
                            is_summary_valid = True
                            logger.info(f"从 RSS summary 获取到有效 desc (可能较长, len={len(cleaned_summary_text)}): {entry_data['title'][:30]}...")
                        
                        # Log reason for invalidity if parsing succeeded but checks failed
                        if not is_summary_valid and cleaned_summary_text:
                            if len(cleaned_summary_text) <= MIN_DESC_LENGTH:
                                reason = "太短"
                            elif cleaned_summary_text.startswith("点击查看原文") or "href=" in cleaned_summary_text[:20]:
                                reason = "像链接或固定文本"
                            else: # Ensure this else aligns correctly
                                reason = "未知原因(非太短/非链接)" # More specific
                            logger.info(f"RSS summary 无效 ({reason})，将不使用: '{cleaned_summary_text[:50]}...' for {entry_data['title'][:30]}")
                        elif not is_summary_valid and not cleaned_summary_text: # Align elif correctly
                            logger.info(f"RSS summary 为空或解析失败 for {entry_data['title'][:30]}")
                        
                        all_articles.append(article_data)
                        articles_count += 1 # Increment counter

                except Exception as entry_err: # Catch errors for this specific entry
                    entry_link = "N/A"
                    if hasattr(entry, 'link'):
                        entry_link = entry.link
                    elif hasattr(entry, 'get'):
                        entry_link = entry.get('link', 'N/A')
                    logger.error(f"处理单个 RSS 源 '{rss_url}' 的条目时出错: {entry_err}. Entry URL: {entry_link}")
                    # Continue to the next entry
                    continue

            logger.info(f"从单个RSS源 {rss_url} 成功处理 {articles_count} 篇最近{days}天的文章") # Log successful count
        except Exception as e:
            logger.error(f"处理单个 RSS 源 {rss_url} 时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc()) # Log full traceback

    else:
        logger.warning("未提供任何RSS源，无法获取文章")
    
    logger.info(f"总共从所有RSS源获取到 {len(all_articles)} 篇最近{days}天的文章")
    return all_articles

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

def fetch_twitter_feed(days_to_fetch=2):
    """
    从 GitHub Raw URL 获取最近几天的推文 JSON 数据并格式化。

    参数:
        days_to_fetch (int): 获取最近多少天的数据，默认为2天。

    返回:
        list: 包含格式化后推文数据的列表，格式同 hotspot_data。
    """
    all_tweets_formatted = []
    base_url = "https://raw.githubusercontent.com/tuber0613/x-kit/main/tweets/"
    today = datetime.now()

    logger.info(f"开始获取最近 {days_to_fetch} 天的 Twitter Feed...")

    for i in range(days_to_fetch):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        file_url = f"{base_url}{date_str}.json"
        logger.info(f"尝试获取推文文件: {file_url}")

        try:
            # 使用 requests 获取 JSON 文件，GitHub Raw 一般不需要 cloudscraper
            response = requests.get(file_url, timeout=15)

            # 检查是否成功获取
            if response.status_code == 404:
                logger.warning(f"未找到 {date_str} 的推文文件，跳过: {file_url}")
                continue
            response.raise_for_status() # 检查其他 HTTP 错误

            # 解析 JSON 数据
            tweets_data = response.json()

            if not isinstance(tweets_data, list):
                 logger.warning(f"获取到的推文数据格式不是列表，跳过: {file_url}")
                 continue

            logger.info(f"成功获取并解析 {date_str} 的推文，共 {len(tweets_data)} 条")

            # 格式化推文数据
            for tweet in tweets_data:
                try:
                    # 解析创建时间
                    # 格式: Sat Mar 29 07:42:16 +0000 2025
                    created_at_str = tweet.get("createdAt")
                    created_at_dt = None
                    timestamp_ms = None
                    published_str = ""
                    if created_at_str:
                        try:
                            # Python 3.7+ 支持 %z 解析 +0000
                            created_at_dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
                            timestamp_ms = int(created_at_dt.timestamp() * 1000)
                            published_str = created_at_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except ValueError as time_err:
                            logger.warning(f"解析推文时间失败: {created_at_str}, 错误: {time_err}")
                            # 如果解析失败，可以尝试其他格式或跳过时间戳

                    # 构建标题 (取 fullText 前 47 个字符 + ...)
                    full_text = tweet.get("fullText", "")
                    if len(full_text) > 50:
                        title = full_text[:47] + "..."
                    else:
                        title = full_text # Use full text if shorter than 50

                    # 获取来源
                    source_name = "Twitter"
                    if tweet.get("user") and tweet["user"].get("screenName"):
                        source_name = f"Twitter-{tweet['user']['screenName']}"

                    # 格式化为标准字典
                    formatted_tweet = {
                        "title": title,
                        "url": tweet.get("tweetUrl", ""),
                        "source": source_name,
                        "content": tweet.get("fullText", ""), # 使用 fullText 作为内容
                        "hot": "", # 推文没有热度值
                        "time": published_str, # 使用格式化后的时间字符串
                        "timestamp": timestamp_ms, # 使用毫秒级时间戳
                        "published": published_str, # 重复添加 published 字段以兼容 RSS 格式
                        "desc": full_text, # Use full tweet text as initial description
                    }
                    # 推文没有预设摘要，所以不添加 desc 字段

                    all_tweets_formatted.append(formatted_tweet)

                except Exception as format_err:
                    logger.error(f"格式化推文时出错: {format_err}, 推文 URL: {tweet.get('tweetUrl')}")

        except requests.exceptions.RequestException as req_err:
            logger.error(f"获取推文文件失败: {file_url}, 错误: {req_err}")
        except json.JSONDecodeError as json_err:
            logger.error(f"解析推文 JSON 失败: {file_url}, 错误: {json_err}")
        except Exception as e:
            logger.error(f"处理推文文件时发生未知错误: {file_url}, 错误: {e}")

    logger.info(f"总共获取并格式化了 {len(all_tweets_formatted)} 条推文")
    return all_tweets_formatted