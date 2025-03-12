#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网页内容爬取：获取到url后，对网页的指定内容进行提取
"""

import requests
import re
import time
import logging
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

def fetch_webpage_content(url, timeout=10, max_retries=3):
    """
    获取网页内容，返回处理后的文本内容和原始HTML
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 设置更多选项以提高稳定性
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
            response.raise_for_status()
            
            # 获取原始HTML内容
            html_content = response.text
            
            # 使用BeautifulSoup处理HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取文本内容
            text_content = soup.get_text(separator=' ', strip=True)
            
            # 预处理文本内容
            processed_content = preprocess_webpage_content(text_content)
            
            logger.info(f"获取到网页内容: {url}, 原始HTML长度: {len(html_content)}, 处理后文本长度: {len(processed_content)} 字符")
            
            return processed_content, html_content
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"获取网页内容失败: {url}, 错误: {str(e)}，5秒后重试 ({retry_count}/{max_retries})...")
                time.sleep(5)
            else:
                logger.error(f"获取网页内容失败: {url}, 错误: {str(e)}")
                return "", ""

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
    
    # 3. 如果内容太长，保留前2000字符（考虑到后续会截断）
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
    """
    if not html_content:
        return None
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. 尝试从meta标签中提取时间
        meta_tags = [
            soup.find('meta', property='article:published_time'),
            soup.find('meta', property='og:published_time'),
            soup.find('meta', property='publish_date'),
            soup.find('meta', itemprop='datePublished'),
            soup.find('meta', name='pubdate'),
            soup.find('meta', name='publishdate'),
            soup.find('meta', name='date')
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