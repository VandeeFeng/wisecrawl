#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网页内容爬取：获取到url后，对网页的指定内容进行提取
使用newspaper3k和trafilatura库进行智能内容提取
"""

import requests
import cloudscraper # 导入 cloudscraper
import re
import time
import logging
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from datetime import datetime

# 导入专业的新闻内容提取库
import newspaper
from newspaper import Article
import trafilatura
from trafilatura.settings import use_config
from trafilatura import extract

# 配置日志
logger = logging.getLogger(__name__)

def fetch_webpage_content(url, timeout=20, max_retries=3, existing_content=None, fetch_html_only=False):
    """
    获取网页内容，返回处理后的文本内容和原始HTML
    如果提供了existing_content，则直接使用该内容而不进行爬取
    使用cloudscraper尝试绕过Cloudflare，然后使用多种方法提取内容
    If fetch_html_only is True, then only get the raw HTML, without extracting the text content.
    """
    # 如果已有内容，并且不是只获取HTML，直接返回
    if existing_content is not None and not fetch_html_only:
        logger.info(f"使用已有内容，跳过爬取: {url}, 内容长度: {len(existing_content)} 字符")
        # Even if using existing content, we might need HTML later for timestamp extraction, 
        # but we don't have it if we skip fetching. Return None for HTML in this case.
        # If fetch_html_only was True, this block is skipped anyway.
        return existing_content, None 
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 创建 cloudscraper 实例
            # 可以配置浏览器类型等，这里使用默认设置
            scraper = cloudscraper.create_scraper(
                # 可以添加一些浏览器伪装选项
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )

            # 使用 scraper.get 获取网页，它会自动处理 Cloudflare 挑战
            # 注意：cloudscraper 可能需要更长的超时时间
            response = scraper.get(url, timeout=timeout, verify=True, allow_redirects=True)
            response.raise_for_status() # 检查请求是否成功 (cloudscraper 失败时也会抛出异常)

            # 获取原始HTML内容
            html_content = response.text

            # 如果只需要HTML，直接返回
            if fetch_html_only:
                logger.info(f"仅获取原始HTML: {url}, HTML长度: {len(html_content)}")
                return None, html_content # Return None for content, as it wasn't extracted

            # 使用多种方法提取内容，优先使用专业的新闻内容提取库
            processed_content = extract_content_with_multiple_methods(html_content, url)
            
            logger.info(f"获取到网页内容: {url}, 原始HTML长度: {len(html_content)}, 处理后文本长度: {len(processed_content)} 字符")
            
            return processed_content, html_content
        except Exception as e:
            # 检查是否是 cloudscraper 特有的错误
            if "CloudflareJSChallengeError" in str(e) or "CloudflareCaptchaError" in str(e):
                 logger.warning(f"Cloudscraper 未能绕过 Cloudflare 保护: {url}, 错误: {str(e)}")
                 # 遇到无法绕过的 Cloudflare 保护，不再重试
                 return "", ""
            # 其他错误，执行重试逻辑
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"获取网页内容失败: {url}, 错误: {str(e)}，{5 * retry_count}秒后重试 ({retry_count}/{max_retries})...")
                time.sleep(5 * retry_count) # 增加重试等待时间
            else:
                logger.error(f"获取网页内容失败: {url}, 错误: {str(e)}")
                return "", ""

def extract_content_with_multiple_methods(html_content, url):
    """
    使用多种方法提取网页内容，按优先级尝试不同的提取方法
    1. trafilatura - 专为网页内容提取设计，对新闻文章效果很好
    2. newspaper3k - 专为新闻内容提取设计
    3. 传统的BeautifulSoup提取 - 作为备选方案
    """
    extracted_content = ""
    
    # 方法1: 使用trafilatura提取内容（专为网页内容提取设计）
    try:
        # 配置trafilatura以提取更完整的内容
        traf_config = use_config()
        traf_config.set("DEFAULT", "MIN_OUTPUT_SIZE", "200")
        traf_config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "200")
        
        # 提取正文内容
        extracted_content = extract(html_content, config=traf_config, url=url, include_comments=False, include_tables=True)
        
        if extracted_content and len(extracted_content.strip()) > 200:
            logger.info(f"使用trafilatura成功提取内容，长度: {len(extracted_content)} 字符")
            return extracted_content
        else:
            logger.info("trafilatura提取内容失败或内容过短，尝试其他方法")
    except Exception as e:
        logger.warning(f"使用trafilatura提取内容时出错: {str(e)}")
    
    # 方法2: 使用newspaper3k提取内容（专为新闻内容提取设计）
    try:
        # 配置newspaper，禁用下载多媒体内容以提高速度
        article = Article(url, language='zh')
        article.download(input_html=html_content)  # 使用已获取的HTML内容
        article.parse()
        
        # 获取正文内容
        if article.text and len(article.text.strip()) > 200:
            extracted_content = article.text
            logger.info(f"使用newspaper3k成功提取内容，长度: {len(extracted_content)} 字符")
            return extracted_content
        else:
            logger.info("newspaper3k提取内容失败或内容过短，尝试其他方法")
    except Exception as e:
        logger.warning(f"使用newspaper3k提取内容时出错: {str(e)}")
    
    # 方法3: 使用传统的BeautifulSoup提取（作为备选方案）
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除不需要的元素
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # 尝试找到主要内容区域
        main_content = None
        
        # 常见的内容容器ID和类名
        content_selectors = [
            "article", ".article", "#article", ".post", "#post", ".content", "#content",
            ".main-content", "#main-content", ".entry-content", "#entry-content",
            ".post-content", "#post-content", ".article-content", "#article-content"
        ]
        
        # 尝试找到主要内容区域
        for selector in content_selectors:
            if selector.startswith("."):
                elements = soup.find_all(class_=selector[1:])
            elif selector.startswith("#"):
                elements = [soup.find(id=selector[1:])]
            else:
                elements = soup.find_all(selector)
            
            # 找到最长的内容区域
            for element in elements:
                if element and (not main_content or len(element.get_text()) > len(main_content.get_text())):
                    main_content = element
        
        # 如果找到了主要内容区域，提取文本
        if main_content:
            text_content = main_content.get_text(separator=' ', strip=True)
        else:
            # 如果没有找到主要内容区域，提取整个body的文本
            text_content = soup.get_text(separator=' ', strip=True)
        
        # 预处理文本内容
        extracted_content = preprocess_webpage_content(text_content)
        logger.info(f"使用BeautifulSoup提取内容，长度: {len(extracted_content)} 字符")
        return extracted_content
    except Exception as e:
        logger.warning(f"使用BeautifulSoup提取内容时出错: {str(e)}")
    
    # 如果所有方法都失败，返回空字符串
    logger.error("所有内容提取方法均失败")
    return ""

def preprocess_webpage_content(content):
    """
    预处理网页内容，去除无关内容，提取核心文本
    """
    if not content:
        return ""
    
    # 1. 去除多余空白字符
    content = ' '.join(content.split())
    
    # 2. 去除常见的网页噪音
    noise_patterns = [
        r'版权所有.*?保留所有权利',
        r'Copyright.*?Reserved',
        r'免责声明.*?',
        r'隐私政策.*?',
        r'登录.*?注册',
        r'关注我们.*?',
        r'点击查看.*?',
        r'相关阅读.*?',
        r'猜你喜欢.*?',
        r'广告.*?',
        r'评论.*?',
    ]
    
    for pattern in noise_patterns:
        content = re.sub(pattern, ' ', content, flags=re.IGNORECASE)
    
    # 3. 如果内容太长，保留前3000字符（考虑到后续会截断）
    if len(content) > 3000:
        # 记录截断信息
        logger.info(f"内容过长，从 {len(content)} 字符截断至 3000 字符")
        
        # 尝试在句子边界截断
        sentences = re.split(r'[.。!！?？;；]', content[:3000])
        if len(sentences) > 1:
            # 保留完整句子
            content = '.'.join(sentences[:-1]) + '.'
        else:
            content = content[:3000]
    
    return content

def extract_publish_time_from_html(html_content, url):
    """
    从HTML内容中提取发布时间
    支持多种常见的时间格式和HTML结构
    优先使用newspaper3k和trafilatura提取
    """
    if not html_content:
        return None
    
    try:
        # 方法1: 使用newspaper3k提取发布时间
        try:
            article = Article(url, language='zh')
            article.download(input_html=html_content)
            article.parse()
            
            if article.publish_date:
                logger.info(f"使用newspaper3k成功提取发布时间: {article.publish_date}")
                return article.publish_date
        except Exception as e:
            logger.debug(f"使用newspaper3k提取发布时间失败: {str(e)}")
        
        # 方法2: 使用trafilatura提取元数据
        try:
            metadata = trafilatura.extract_metadata(html_content, url=url)
            if metadata and metadata.date:
                date_obj = date_parser.parse(metadata.date)
                logger.info(f"使用trafilatura成功提取发布时间: {date_obj}")
                return date_obj
        except Exception as e:
            logger.debug(f"使用trafilatura提取发布时间失败: {str(e)}")
        
        # 方法3: 使用传统方法提取
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. 尝试从meta标签中提取时间
        meta_tags = [
            soup.find('meta', attrs={'property': 'article:published_time'}),
            soup.find('meta', attrs={'property': 'og:published_time'}),
            soup.find('meta', attrs={'property': 'publish_date'}),
            soup.find('meta', attrs={'itemprop': 'datePublished'}),
            soup.find('meta', attrs={'name': 'pubdate'}),
            soup.find('meta', attrs={'name': 'publishdate'}),
            soup.find('meta', attrs={'name': 'date'})
        ]
        
        for tag in meta_tags:
            if tag and tag.get('content'):
                try:
                    return date_parser.parse(tag.get('content'))
                except:
                    pass
        
        # 2. 尝试从time标签中提取
        time_tags = soup.find_all('time')
        for time_tag in time_tags:
            datetime_attr = time_tag.get('datetime')
            if datetime_attr:
                try:
                    return date_parser.parse(datetime_attr)
                except:
                    pass
        
        # 3. 针对特定网站的自定义提取逻辑
        if 'juejin.cn' in url:
            # 掘金网站的时间提取
            time_elements = soup.find_all('time', class_='time')
            for time_element in time_elements:
                if time_element.get('datetime'):
                    try:
                        return date_parser.parse(time_element.get('datetime'))
                    except:
                        pass
        
        # 4. 尝试从常见的日期格式中提取
        date_patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # 2024-03-08 12:34:56
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # 2024-03-08T12:34:56
            r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}',        # 2024/03/08 12:34
            r'\d{4}年\d{1,2}月\d{1,2}日 \d{1,2}:\d{1,2}',  # 2024年3月8日 12:34
            r'\d{4}年\d{1,2}月\d{1,2}日',            # 2024年3月8日
            r'\d{4}-\d{2}-\d{2}'                     # 2024-03-08
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                try:
                    return date_parser.parse(matches[0])
                except:
                    pass
        
        logger.debug(f"无法从HTML内容中提取发布时间: {url}")
        return None
    
    except Exception as e:
        logger.warning(f"提取发布时间时发生错误: {str(e)}, URL: {url}")
        return None