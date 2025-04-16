import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


def extract_rss_entry(entry: Any) -> Dict[str, Any]:
    """
    Extract standardized information from an RSS entry
    
    Parameters:
        entry: Single entry after feedparser parsing
        
    Returns:
        Dictionary containing standardized information
    """
    result = {
        "title": "",
        "link": "",
        "author": "Unknown Author",
        "published": "",
        "content": "",
        "summary": ""
    }
    
    # 1. Extract title
    result["title"] = _extract_title(entry)
    
    # 2. Extract link
    result["link"] = _extract_link(entry)
    
    # 3. Extract author
    result["author"] = _extract_author(entry)
    
    # 4. Extract publish time
    pub_time = _extract_publish_time(entry)
    if pub_time:
        result["published"] = pub_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 5. Extract content
    result["content"] = _extract_content(entry)
    
    # 6. Extract summary
    result["summary"] = _extract_summary(entry)
    
    return result


def _extract_title(entry: Any) -> str:
    """
    Extract title
    """
    if not hasattr(entry, 'title'):
        return "No Title"
    
    title = entry.title
    
    # Handle case where title is a dictionary
    if isinstance(title, dict) and 'value' in title:
        title = title.value
    
    # Handle CDATA tags
    if isinstance(title, str) and title.startswith('<![CDATA[') and title.endswith(']]>'):
        title = title[9:-3]  # Remove CDATA tags
    
    return title


def _extract_link(entry: Any) -> str:
    """
    Extract link
    """
    if not hasattr(entry, 'link'):
        return ""
    
    # Handle case where link is a string
    if isinstance(entry.link, str):
        return entry.link
    
    # Handle case where link is a dictionary (common in Atom format)
    if isinstance(entry.link, dict) and 'href' in entry.link:
        return entry.link.href
    
    # Handle case where link is a list
    if isinstance(entry.link, list) and len(entry.link) > 0:
        for link_item in entry.link:
            if isinstance(link_item, dict) and 'href' in link_item:
                # Prioritize links with rel="alternate"
                if link_item.get('rel') == 'alternate':
                    return link_item['href']
        # If no rel="alternate" found, use the first link with href
        for link_item in entry.link:
            if isinstance(link_item, dict) and 'href' in link_item:
                return link_item['href']
    
    # Try other possible attributes
    if hasattr(entry, 'links') and isinstance(entry.links, list):
        for link_item in entry.links:
            if isinstance(link_item, dict) and 'href' in link_item:
                return link_item['href']
    
    return ""


def _extract_author(entry: Any) -> str:
    """
    Extract author information
    """
    if not hasattr(entry, 'author'):
        return "Unknown Author"
    
    # Handle case where author is a dictionary (common in Atom format)
    if isinstance(entry.author, dict) and 'name' in entry.author:
        return entry.author.name
    
    # Handle case where author is a string
    return str(entry.author)


def _extract_publish_time(entry: Any) -> Optional[datetime]:
    """
    Extract publish time
    """
    # Prefer published_parsed field
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime.fromtimestamp(time.mktime(entry.published_parsed))
    
    # Otherwise use updated_parsed field
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime.fromtimestamp(time.mktime(entry.updated_parsed))
    
    return None


def _extract_content(entry: Any) -> str:
    """
    Extract content, with priority:
    1. content field
    2. content:encoded field
    3. description field (for special sources like Jiqizhixin)
    4. summary field (for special sources like Jiqizhixin)
    """
    # 1. Try to get content from content field
    if hasattr(entry, 'content') and entry.content:
        content_value = ""
        
        # Handle case where content is a list
        if isinstance(entry.content, list) and len(entry.content) > 0:
            content_item = entry.content[0]
            
            # Handle case where content_item is a dictionary
            if isinstance(content_item, dict) and 'value' in content_item:
                content_value = content_item['value']
            # Handle case where content_item has value attribute
            elif hasattr(content_item, 'value'):
                content_value = content_item.value
            # Otherwise, convert to string
            else:
                content_value = str(content_item)
            
            if content_value and len(content_value.strip()) > 20:
                return content_value
    
    # 2. Try to get content from content:encoded field
    content_encoded = None
    
    # Directly as attribute
    if hasattr(entry, 'content_encoded'):
        content_encoded = entry.content_encoded
    # As dictionary item
    elif hasattr(entry, 'get') and callable(getattr(entry, 'get')) and entry.get('content_encoded'):
        content_encoded = entry.get('content_encoded')
    
    if content_encoded:
        # Handle CDATA tags
        if isinstance(content_encoded, str) and content_encoded.startswith('<![CDATA[') and content_encoded.endswith(']]>'):
            content_encoded = content_encoded[9:-3]
        
        if len(content_encoded.strip()) > 20:
            return content_encoded
    
    # 3. Try to get content from description field (effective for special sources like Jiqizhixin)
    if hasattr(entry, 'description') and entry.description:
        desc = entry.description
        # Handle CDATA tags
        if isinstance(desc, str) and desc.startswith('<![CDATA[') and desc.endswith(']]>'):
            desc = desc[9:-3]
        
        if len(desc.strip()) > 20:
            return desc
    
    # 4. Try to get content from summary field (effective for special sources like Jiqizhixin)
    if hasattr(entry, 'summary') and entry.summary:
        summary = entry.summary
        # Handle CDATA tags
        if isinstance(summary, str) and summary.startswith('<![CDATA[') and summary.endswith(']]>'):
            summary = summary[9:-3]
        
        if len(summary.strip()) > 20:
            return summary
    
    # 5. Try to get content from source field (effective for special sources like Jiqizhixin)
    if hasattr(entry, 'source') and isinstance(entry.source, dict):
        # Check title in source field
        if 'title' in entry.source and entry.source['title']:
            # For Jiqizhixin, we can use the title as part of the content
            return f"Source: {entry.source['title']}, Title: {entry.title if hasattr(entry, 'title') else 'No Title'}"
        
        # Check value in source field
        if 'value' in entry.source and entry.source['value']:
            source_value = entry.source['value']
            if len(source_value.strip()) > 20:
                return source_value
    
    return ""


def _extract_summary(entry: Any) -> str:
    """
    Extract summary
    """
    if not hasattr(entry, 'summary'):
        return ""
    
    summary = entry.summary
    
    # Handle case where summary is a dictionary
    if isinstance(summary, dict) and 'value' in summary:
        summary = summary['value']
    
    # Handle CDATA tags
    if isinstance(summary, str) and summary.startswith('<![CDATA[') and summary.endswith(']]>'):
        summary = summary[9:-3]
    
    # If summary is empty, try to use description field
    if not summary or len(summary.strip()) < 20:
        if hasattr(entry, 'description') and entry.description:
            desc = entry.description
            if isinstance(desc, str) and desc.startswith('<![CDATA[') and desc.endswith(']]>'):
                desc = desc[9:-3]
            if len(desc.strip()) > 20:
                return desc
    
    return summary