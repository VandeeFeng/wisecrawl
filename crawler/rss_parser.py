#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RSS解析器：提供标准化的RSS内容提取功能
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


def extract_rss_entry(entry: Any) -> Dict[str, Any]:
    """
    从RSS条目中提取标准化的信息
    
    参数:
        entry: feedparser解析后的单个条目
        
    返回:
        包含标准化信息的字典
    """
    result = {
        "title": "",
        "link": "",
        "author": "未知作者",
        "published": "",
        "content": "",
        "summary": ""
    }
    
    # 1. 提取标题
    result["title"] = _extract_title(entry)
    
    # 2. 提取链接
    result["link"] = _extract_link(entry)
    
    # 3. 提取作者
    result["author"] = _extract_author(entry)
    
    # 4. 提取发布时间
    pub_time = _extract_publish_time(entry)
    if pub_time:
        result["published"] = pub_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 5. 提取内容
    result["content"] = _extract_content(entry)
    
    # 6. 提取摘要
    result["summary"] = _extract_summary(entry)
    
    return result


def _extract_title(entry: Any) -> str:
    """
    提取标题
    """
    if not hasattr(entry, 'title'):
        return "无标题"
    
    title = entry.title
    
    # 处理标题是字典的情况
    if isinstance(title, dict) and 'value' in title:
        title = title.value
    
    # 处理CDATA标签
    if isinstance(title, str) and title.startswith('<![CDATA[') and title.endswith(']]>'):
        title = title[9:-3]  # 去除CDATA标签
    
    return title


def _extract_link(entry: Any) -> str:
    """
    提取链接
    """
    if not hasattr(entry, 'link'):
        return ""
    
    # 处理链接是字符串的情况
    if isinstance(entry.link, str):
        return entry.link
    
    # 处理链接是字典的情况（Atom格式常见）
    if isinstance(entry.link, dict) and 'href' in entry.link:
        return entry.link.href
    
    # 处理链接是列表的情况
    if isinstance(entry.link, list) and len(entry.link) > 0:
        for link_item in entry.link:
            if isinstance(link_item, dict) and 'href' in link_item:
                # 优先选择rel="alternate"的链接
                if link_item.get('rel') == 'alternate':
                    return link_item['href']
        # 如果没有找到rel="alternate"，使用第一个有href的链接
        for link_item in entry.link:
            if isinstance(link_item, dict) and 'href' in link_item:
                return link_item['href']
    
    # 尝试其他可能的属性
    if hasattr(entry, 'links') and isinstance(entry.links, list):
        for link_item in entry.links:
            if isinstance(link_item, dict) and 'href' in link_item:
                return link_item['href']
    
    return ""


def _extract_author(entry: Any) -> str:
    """
    提取作者信息
    """
    if not hasattr(entry, 'author'):
        return "未知作者"
    
    # 处理作者是字典的情况（Atom格式常见）
    if isinstance(entry.author, dict) and 'name' in entry.author:
        return entry.author.name
    
    # 处理作者是字符串的情况
    return str(entry.author)


def _extract_publish_time(entry: Any) -> Optional[datetime]:
    """
    提取发布时间
    """
    # 首选published_parsed字段
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime.fromtimestamp(time.mktime(entry.published_parsed))
    
    # 其次使用updated_parsed字段
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime.fromtimestamp(time.mktime(entry.updated_parsed))
    
    return None


def _extract_content(entry: Any) -> str:
    """
    提取内容，优先级：
    1. content字段
    2. content:encoded字段
    3. description字段（对于机器之心等特殊源）
    4. summary字段（对于机器之心等特殊源）
    """
    # 1. 尝试从content字段获取内容
    if hasattr(entry, 'content') and entry.content:
        content_value = ""
        
        # 处理content是列表的情况
        if isinstance(entry.content, list) and len(entry.content) > 0:
            content_item = entry.content[0]
            
            # 处理content_item是字典的情况
            if isinstance(content_item, dict) and 'value' in content_item:
                content_value = content_item['value']
            # 处理content_item有value属性的情况
            elif hasattr(content_item, 'value'):
                content_value = content_item.value
            # 其他情况，转为字符串
            else:
                content_value = str(content_item)
            
            if content_value and len(content_value.strip()) > 20:
                return content_value
    
    # 2. 尝试从content:encoded字段获取内容
    content_encoded = None
    
    # 直接作为属性
    if hasattr(entry, 'content_encoded'):
        content_encoded = entry.content_encoded
    # 作为字典项
    elif hasattr(entry, 'get') and callable(getattr(entry, 'get')) and entry.get('content_encoded'):
        content_encoded = entry.get('content_encoded')
    
    if content_encoded:
        # 处理CDATA标签
        if isinstance(content_encoded, str) and content_encoded.startswith('<![CDATA[') and content_encoded.endswith(']]>'):
            content_encoded = content_encoded[9:-3]
        
        if len(content_encoded.strip()) > 20:
            return content_encoded
    
    # 3. 尝试从description字段获取内容（对机器之心等特殊源有效）
    if hasattr(entry, 'description') and entry.description:
        desc = entry.description
        # 处理CDATA标签
        if isinstance(desc, str) and desc.startswith('<![CDATA[') and desc.endswith(']]>'):
            desc = desc[9:-3]
        
        if len(desc.strip()) > 20:
            return desc
    
    # 4. 尝试从summary字段获取内容（对机器之心等特殊源有效）
    if hasattr(entry, 'summary') and entry.summary:
        summary = entry.summary
        # 处理CDATA标签
        if isinstance(summary, str) and summary.startswith('<![CDATA[') and summary.endswith(']]>'):
            summary = summary[9:-3]
        
        if len(summary.strip()) > 20:
            return summary
    
    # 5. 尝试从source字段获取内容（对机器之心等特殊源有效）
    if hasattr(entry, 'source') and isinstance(entry.source, dict):
        # 检查source字段中的title
        if 'title' in entry.source and entry.source['title']:
            # 对于机器之心，我们可以使用标题作为内容的一部分
            return f"来源: {entry.source['title']}，标题: {entry.title if hasattr(entry, 'title') else '无标题'}"
        
        # 检查source字段中的value
        if 'value' in entry.source and entry.source['value']:
            source_value = entry.source['value']
            if len(source_value.strip()) > 20:
                return source_value
    
    return ""


def _extract_summary(entry: Any) -> str:
    """
    提取摘要
    """
    if not hasattr(entry, 'summary'):
        return ""
    
    summary = entry.summary
    
    # 处理summary是字典的情况
    if isinstance(summary, dict) and 'value' in summary:
        summary = summary['value']
    
    # 处理CDATA标签
    if isinstance(summary, str) and summary.startswith('<![CDATA[') and summary.endswith(']]>'):
        summary = summary[9:-3]
    
    # 如果摘要为空，尝试使用description字段
    if not summary or len(summary.strip()) < 20:
        if hasattr(entry, 'description') and entry.description:
            desc = entry.description
            if isinstance(desc, str) and desc.startswith('<![CDATA[') and desc.endswith(']]>'):
                desc = desc[9:-3]
            if len(desc.strip()) > 20:
                return desc
    
    return summary