import requests
import cloudscraper # Import cloudscraper
import re
import time
import logging
import random
from threading import Lock
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from datetime import datetime

# Import professional news content extraction libraries
import newspaper
from newspaper import Article
import trafilatura
from trafilatura.settings import use_config
from trafilatura import extract

# Configure logging
logger = logging.getLogger(__name__)

# Global request lock
request_lock = Lock()

def fetch_webpage_content(url, timeout=20, max_retries=3, existing_content=None, fetch_html_only=False):
    """
    Get webpage content, return processed text content and original HTML
    If existing_content is provided, use it directly without crawling
    Use cloudscraper to try to bypass Cloudflare, then use multiple methods to extract content
    If fetch_html_only is True, then only get the raw HTML, without extracting the text content.
    """
    # Check if there is substantial existing content (length greater than 10 after removing leading and trailing spaces)
    has_substantial_existing_content = (
        existing_content is not None and len(existing_content.strip()) > 10
    )
    # Only skip crawling if there is substantial content and not only getting HTML
    if has_substantial_existing_content and not fetch_html_only:
        logger.info(f"Detected existing substantial content ({len(existing_content)} characters), skipping crawling: {url}")
        return existing_content, None 
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Use lock to ensure only one request at a time
            with request_lock:
                # Add random delay to avoid frequent requests
                if retry_count > 0:
                    delay = random.uniform(1, 5)
                    logger.info(f"Waiting {delay:.2f} seconds before retrying...")
                    time.sleep(delay)

                # Create cloudscraper instance
                scraper = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False
                    }
                )

                # Use scraper.get to get webpage
                response = scraper.get(url, timeout=timeout, verify=True, allow_redirects=True)
                response.raise_for_status()

                # Get original HTML content
                html_content = response.text

                # If only HTML is needed, return directly
                if fetch_html_only:
                    logger.info(f"Only getting original HTML: {url}, HTML length: {len(html_content)}")
                    return None, html_content

                # Use multiple methods to extract content
                processed_content = extract_content_with_multiple_methods(html_content, url)
                
                logger.info(f"Got webpage content: {url}, original HTML length: {len(html_content)}, processed text length: {len(processed_content)} characters")
                
                return processed_content, html_content

        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Failed to get webpage content: {url}, error: {str(e)}, will add random delay on next retry...")
            else:
                logger.error(f"Failed to get webpage content: {url}, error: {str(e)}")
                return "", ""

def extract_content_with_multiple_methods(html_content, url):
    """
    Extract webpage content using multiple methods, try different extraction methods by priority
    1. trafilatura - designed for webpage content extraction, works well for news articles
    2. newspaper3k - designed for news content extraction
    3. Traditional BeautifulSoup extraction - as a fallback
    """
    extracted_content = ""
    
    # Method 1: Use trafilatura to extract content (designed for webpage content extraction)
    try:
        # Configure trafilatura to extract more complete content
        traf_config = use_config()
        traf_config.set("DEFAULT", "MIN_OUTPUT_SIZE", "200")
        traf_config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "200")
        
        # Extract main content
        extracted_content = extract(html_content, config=traf_config, url=url, include_comments=False, include_tables=True)
        
        if extracted_content and len(extracted_content.strip()) > 200:
            logger.info(f"Successfully extracted content using trafilatura, length: {len(extracted_content)} characters")
            return extracted_content
        else:
            logger.info("Failed to extract content using trafilatura or content too short, trying other methods")
    except Exception as e:
        logger.warning(f"Error extracting content using trafilatura: {str(e)}")
    
    # Method 2: Use newspaper3k to extract content (designed for news content extraction)
    try:
        # Configure newspaper, disable downloading multimedia content to improve speed
        article = Article(url, language='zh')
        article.download(input_html=html_content)  # Use already obtained HTML content
        article.parse()
        
        # Get main content
        if article.text and len(article.text.strip()) > 200:
            extracted_content = article.text
            logger.info(f"Successfully extracted content using newspaper3k, length: {len(extracted_content)} characters")
            return extracted_content
        else:
            logger.info("Failed to extract content using newspaper3k or content too short, trying other methods")
    except Exception as e:
        logger.warning(f"Error extracting content using newspaper3k: {str(e)}")
    
    # Method 3: Use traditional BeautifulSoup extraction (as a fallback)
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Try to find main content area
        main_content = None
        
        # Common content container IDs and class names
        content_selectors = [
            "article", ".article", "#article", ".post", "#post", ".content", "#content",
            ".main-content", "#main-content", ".entry-content", "#entry-content",
            ".post-content", "#post-content", ".article-content", "#article-content"
        ]
        
        # Try to find main content area
        for selector in content_selectors:
            if selector.startswith("."):
                elements = soup.find_all(class_=selector[1:])
            elif selector.startswith("#"):
                elements = [soup.find(id=selector[1:])]
            else:
                elements = soup.find_all(selector)
            
            # Find the longest content area
            for element in elements:
                if element and (not main_content or len(element.get_text()) > len(main_content.get_text())):
                    main_content = element
        
        # If main content area is found, extract text
        if main_content:
            text_content = main_content.get_text(separator=' ', strip=True)
        else:
            # If no main content area is found, extract text from the entire body
            text_content = soup.get_text(separator=' ', strip=True)
        
        # Preprocess text content
        extracted_content = preprocess_webpage_content(text_content)
        logger.info(f"Extracted content using BeautifulSoup, length: {len(extracted_content)} characters")
        return extracted_content
    except Exception as e:
        logger.warning(f"Error extracting content using BeautifulSoup: {str(e)}")
    
    # If all methods fail, return empty string
    logger.error("All content extraction methods failed")
    return ""

def preprocess_webpage_content(content):
    """
    Preprocess webpage content, remove irrelevant content, extract core text
    """
    if not content:
        return ""
    
    # 1. Remove extra whitespace characters
    content = ' '.join(content.split())
    
    # 2. Remove common webpage noise
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
    
    # 3. If content is too long, keep the first 3000 characters (considering later truncation)
    if len(content) > 3000:
        # Log truncation information
        logger.info(f"Content too long, truncated from {len(content)} to 3000 characters")
        
        # Try to truncate at sentence boundaries
        sentences = re.split(r'[.。!！?？;；]', content[:3000])
        if len(sentences) > 1:
            # Keep complete sentences
            content = '.'.join(sentences[:-1]) + '.'
        else:
            content = content[:3000]
    
    return content

def extract_publish_time_from_html(html_content, url):
    """
    Extract publish time from HTML content
    Support multiple common time formats and HTML structures
    Prioritize using newspaper3k and trafilatura extraction
    """
    if not html_content:
        return None
    
    try:
        # Method 1: Use newspaper3k to extract publish time
        try:
            article = Article(url, language='zh')
            article.download(input_html=html_content)
            article.parse()
            
            if article.publish_date:
                logger.info(f"Successfully extracted publish time using newspaper3k: {article.publish_date}")
                return article.publish_date
        except Exception as e:
            logger.warning(f"Failed to extract publish time using newspaper3k: {str(e)}")
        
        # Method 2: Use BeautifulSoup to extract publish time from meta tags
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for common meta tags containing publish time
            meta_tags = {
                'article:published_time': ['property', 'name'],
                'pubdate': ['property', 'name'],
                'publishdate': ['property', 'name'],
                'og:published_time': ['property'],
                'publish_date': ['name'],
                'date': ['name'],
                'published_time': ['name'],
                'datePublished': ['itemprop']
            }
            
            for meta_name, attrs in meta_tags.items():
                for attr in attrs:
                    meta = soup.find('meta', {attr: meta_name})
                    if meta and meta.get('content'):
                        try:
                            pub_date = date_parser.parse(meta['content'])
                            logger.info(f"Extracted publish time from meta tag {attr}={meta_name}: {pub_date}")
                            return pub_date
                        except Exception as e:
                            logger.warning(f"Failed to parse date from meta tag {attr}={meta_name}: {str(e)}")
            
            # Look for time tags
            time_tags = soup.find_all('time')
            for time_tag in time_tags:
                if time_tag.get('datetime'):
                    try:
                        pub_date = date_parser.parse(time_tag['datetime'])
                        logger.info(f"Extracted publish time from time tag: {pub_date}")
                        return pub_date
                    except Exception as e:
                        logger.warning(f"Failed to parse date from time tag: {str(e)}")
            
            # Look for specific JSON-LD scripts containing publish time
            script_tags = soup.find_all('script', {'type': 'application/ld+json'})
            for script in script_tags:
                try:
                    import json
                    data = json.loads(script.string)
                    date_published = None
                    
                    # Check for datePublished in different levels
                    if isinstance(data, dict):
                        date_published = data.get('datePublished')
                        if not date_published and '@graph' in data and isinstance(data['@graph'], list):
                            for item in data['@graph']:
                                if isinstance(item, dict) and 'datePublished' in item:
                                    date_published = item['datePublished']
                                    break
                    
                    if date_published:
                        pub_date = date_parser.parse(date_published)
                        logger.info(f"Extracted publish time from JSON-LD: {pub_date}")
                        return pub_date
                except Exception as e:
                    logger.warning(f"Failed to extract date from JSON-LD: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Failed to extract publish time from HTML: {str(e)}")
        
        # Method 3: Try to find date patterns in URLs
        try:
            # Common date patterns in URLs: /2023/01/15/, /2023-01-15/, etc.
            date_patterns = [
                r'/(\d{4})/(\d{1,2})/(\d{1,2})/',
                r'/(\d{4})-(\d{1,2})-(\d{1,2})/',
                r'[_./-](\d{4})(\d{2})(\d{2})[_./-]'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, url)
                if match:
                    year, month, day = match.groups()
                    try:
                        pub_date = datetime(int(year), int(month), int(day))
                        logger.info(f"Extracted publish time from URL pattern: {pub_date}")
                        return pub_date
                    except Exception as e:
                        logger.warning(f"Failed to create date from URL pattern: {str(e)}")
        except Exception as e:
            logger.warning(f"Failed to extract date from URL: {str(e)}")
        
        logger.warning(f"Could not extract publish time from {url}")
        return None
    
    except Exception as e:
        logger.error(f"Error extracting publish time: {str(e)}")
        return None