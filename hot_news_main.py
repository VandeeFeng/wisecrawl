import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
import warnings

# Filter newspaper package's regex warnings
warnings.filterwarnings('ignore', category=SyntaxWarning, module='newspaper')

# Import configurations
from config.config import (
    TECH_SOURCES, ALL_SOURCES, WEBHOOK_URL, DEEPSEEK_API_KEY, 
    HUNYUAN_API_KEY, BASE_URL, DEEPSEEK_API_URL, DEEPSEEK_MODEL_ID,
    RSS_URL, RSS_DAYS, TITLE_LENGTH, MAX_WORKERS, FILTER_DAYS, RSS_FEEDS
)

# Import utility functions
from utils.utils import save_hotspots_to_jsonl, check_base_url, cleanup_old_files

# Import data collection modules
from crawler.data_collector import (
    collect_all_hotspots, fetch_rss_articles, filter_recent_hotspots,
    fetch_twitter_feed
)

# Import processing module
from processor.news_processor import process_hotspot_with_summary

# Import LLM integration module
from llm_integration.summary_integration import summarize_with_deepseek

# Import notification module
from notification.webhook_sender import notify, send_to_webhook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def str_to_bool(value):
    """
    Convert string to boolean
    """
    if isinstance(value, bool):
        return value
    return value.lower() in ('true', '1', 't', 'y', 'yes')

def main():
    # Read configuration from environment variables, prioritize env vars over config.py defaults
    # Use values directly imported from config, which already handle defaults and env vars
    tech_only = str_to_bool(os.getenv('TECH_ONLY', str(TECH_SOURCES is not None))) # Default depends on TECH_SOURCES definition
    webhook = WEBHOOK_URL
    deepseek_key = DEEPSEEK_API_KEY
    hunyuan_key = HUNYUAN_API_KEY
    no_cache = str_to_bool(os.getenv('NO_CACHE', 'False')) # Keep env var override for this
    base_url = BASE_URL.strip() # Ensure no trailing spaces from env var or default
    deepseek_url = DEEPSEEK_API_URL
    model_id = DEEPSEEK_MODEL_ID
    rss_url = RSS_URL
    rss_days = RSS_DAYS
    title_length = TITLE_LENGTH
    max_workers = MAX_WORKERS
    skip_content = str_to_bool(os.getenv('SKIP_CONTENT', 'False')) # Keep env var override for this
    filter_days = FILTER_DAYS
    
    # --- DEBUGGING --- 
    # print(f"DEBUG: BASE_URL from config.py: '{BASE_URL}'")
    # print(f"DEBUG: base_url local variable (before strip): '{base_url}'")
    base_url = base_url.strip() # Keep the strip() here just in case
    # print(f"DEBUG: base_url local variable (after strip): '{base_url}'")
    # --- END DEBUGGING ---
    
    # Check if required API keys exist
    if not webhook:
        logger.error("No Webhook URL provided. Please set WEBHOOK_URL in environment variables")
        sys.exit(1)
    
    if not deepseek_key:
        logger.error("No Deepseek API Key provided. Please set DEEPSEEK_API_KEY in environment variables")
        sys.exit(1)
    
    if not hunyuan_key and not skip_content:
        logger.error("No Tencent Hunyuan API Key provided. Please set HUNYUAN_API_KEY in environment variables or set SKIP_CONTENT=True to skip content processing")
        sys.exit(1)
    
    # Check if BASE_URL is accessible
    # Clean the base_url before checking
    cleaned_base_url = base_url.rstrip('/') # Remove trailing slash for check_base_url
    # print(f"DEBUG: Value passed to check_base_url: '{cleaned_base_url}'") # Remove debug print
    if not check_base_url(cleaned_base_url):
        logger.error(f"BASE_URL {cleaned_base_url} is not accessible, exiting")
        sys.exit(1)
    
    # Select information sources based on parameters
    sources = TECH_SOURCES if tech_only else ALL_SOURCES
    
    # Collect hotspots
    # Pass the cleaned base_url
    hotspots = collect_all_hotspots(sources, base_url) # Pass the original base_url with potential slash
    
    if not hotspots:
        logger.warning("No hotspot data collected, will try other sources...")
        hotspots = [] # Ensure hotspots is a list
    
    # Save raw hotspot data
    if hotspots:
        save_hotspots_to_jsonl(hotspots, directory=os.path.join("data", "raw")) # Specify raw directory
    
    # Filter recent hotspots
    hotspots = filter_recent_hotspots(hotspots, filter_days)
    
    # Save filtered hotspot data
    if hotspots:
        save_hotspots_to_jsonl(hotspots, directory=os.path.join("data", "filtered"))
    
    # Get RSS articles
    # Prioritize RSS_FEEDS list, if empty use single RSS_URL
    rss_articles = fetch_rss_articles(rss_url=rss_url, days=rss_days, rss_feeds=RSS_FEEDS)
    
    # Get Twitter Feed
    twitter_feed_raw = fetch_twitter_feed(days_to_fetch=2) # Get last 2 days
    
    # Filter tweets, keep only last 24 hours
    recent_tweets = []
    cutoff_time_tweets = datetime.now() - timedelta(days=1)
    if twitter_feed_raw:
        logger.info(f"Start filtering tweets from last 24 hours (cutoff time: {cutoff_time_tweets})...")
        for tweet in twitter_feed_raw:
            if tweet.get("timestamp"): # Ensure timestamp exists
                # Ensure timestamp is treated correctly (it's already in milliseconds from fetch_twitter_feed)
                tweet_time_ms = tweet["timestamp"]
                if isinstance(tweet_time_ms, (int, float)):
                   tweet_time = datetime.fromtimestamp(tweet_time_ms / 1000)
                   if tweet_time >= cutoff_time_tweets:
                       recent_tweets.append(tweet)
                   # else: # Uncomment to see discarded tweets
                   #     logger.debug(f"Discarded older tweet: {tweet['title']} @ {tweet_time}")
                else:
                   logger.warning(f"Invalid tweet timestamp format: {tweet_time_ms}, type: {type(tweet_time_ms)}, skipping tweet: {tweet.get('title')}")

            else:
                 logger.warning(f"Tweet missing timestamp, cannot filter: {tweet.get('title')}")
                 # Decide whether to include tweets without timestamps or skip them
                 # For now, we skip them to ensure only recent ones are included
                 # recent_tweets.append(tweet) # Uncomment to include tweets without timestamp

        logger.info(f"After filtering, kept {len(recent_tweets)}/{len(twitter_feed_raw)} tweets from last 24 hours.")
    
    # Merge hotspots, RSS articles and filtered tweets
    all_content = hotspots + rss_articles + recent_tweets # Add recent_tweets
    logger.info(f"Total {len(all_content)} items after merging (including tweets)")
    
    # Check if there's any content after merging
    if not all_content:
        logger.error("No valid content from any source, exiting")
        sys.exit(1)
    
    # Save merged data
    save_hotspots_to_jsonl(all_content, directory=os.path.join("data", "merged"))
    
    # Get webpage content and generate summaries
    if not skip_content:
        try:
            # Ensure event loop exists
            if asyncio.get_event_loop().is_closed():
                asyncio.set_event_loop(asyncio.new_event_loop())
            
            # Process all content asynchronously
            loop = asyncio.get_event_loop()
            all_content_with_summary = loop.run_until_complete(
                process_hotspot_with_summary(all_content, hunyuan_key, max_workers, 
                                           tech_only, use_cache=not no_cache)
            )
            logger.info(f"Generated summaries for {len(all_content_with_summary)} items")
        except Exception as e:
            logger.error(f"Error getting webpage content or generating summaries: {str(e)}")
            # If error occurs, continue with original content
            all_content_with_summary = all_content
    else:
        all_content_with_summary = all_content
        logger.info("Skipped webpage content retrieval and summary generation")
    
    # Deduplicate based on title, prioritize RSS and Twitter
    logger.info(f"Starting title-based deduplication (prioritizing RSS/Twitter), items before: {len(all_content_with_summary)}")
    seen_titles = {}
    preferred_sources = {"RSS", "Twitter"} # Verify these match source names used in data_collector
    
    for item in all_content_with_summary:
        title = item.get("title", "").strip()
        if not title: # Skip items without title
            continue
            
        current_source = item.get("source", "")
    
        if title not in seen_titles:
            seen_titles[title] = item
        else:
            existing_item = seen_titles[title]
            existing_source = existing_item.get("source", "")
            
            # If current item is from preferred source and existing is not, replace it
            if current_source in preferred_sources and existing_source not in preferred_sources:
                logger.debug(f"Deduplication: Replacing '{title}' (from {existing_source}) with preferred source {current_source}")
                seen_titles[title] = item
            # If both are preferred sources or neither is, keep the first one (current logic)
            # Can add more complex priority rules if needed, e.g., RSS over Twitter
            # else:
            #    logger.debug(f"Deduplication: Keeping '{title}' (from {existing_source}), ignoring from {current_source}")
                
    deduplicated_content = list(seen_titles.values())
    logger.info(f"Items after deduplication: {len(deduplicated_content)}")

    # Save final processed and deduplicated news list
    logger.info(f"Preparing to save {len(deduplicated_content)} processed and deduplicated news items...")
    processed_output_dir = os.path.join("data", "processed_output")
    os.makedirs(processed_output_dir, exist_ok=True) # Ensure directory exists
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    processed_filename = os.path.join(processed_output_dir, f"processed_news_{timestamp_str}.json")
    
    try:
        # HTML tag cleaning function
        def clean_html(text):
            if not isinstance(text, str):
                return text
            # Use BeautifulSoup to clean HTML tags while preserving line breaks
            soup = BeautifulSoup(text, 'html.parser')
            # Convert <br> and </p> tags to newlines
            for br in soup.find_all(['br', 'p']):
                br.replace_with('\n' + br.get_text())
            clean_text = soup.get_text()
            # Clean extra whitespace while preserving line breaks
            lines = clean_text.splitlines()
            cleaned_lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
            # Filter out empty lines and rejoin with newlines
            clean_text = '\n'.join(line for line in cleaned_lines if line)
            return clean_text

        # Recursively clean all string values in dictionary
        def clean_dict(item):
            if isinstance(item, dict):
                return {k: clean_dict(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [clean_dict(i) for i in item]
            elif isinstance(item, str):
                return clean_html(item)
            return item

        # Clean HTML tags from all content
        cleaned_content = [clean_dict(item) for item in deduplicated_content]
        
        # Save to JSON file
        import json 
        with open(processed_filename, 'w', encoding='utf-8') as f:
            json.dump(cleaned_content, f, ensure_ascii=False, indent=4)
        logger.info(f"Successfully saved processed news list (HTML tags cleaned and line breaks preserved) to: {processed_filename}")
    except Exception as e:
        logger.error(f"Error saving processed news list to {processed_filename}: {str(e)}")
    
    # Use Deepseek for summarization
    summary = summarize_with_deepseek(deduplicated_content, deepseek_key,
                                     deepseek_url, model_id, tech_only=tech_only)
    
    # Try multiple notification methods
    success = notify(summary, tech_only)
    if not success:
        # If all configured notification methods fail, try original webhook as fallback
        logger.warning("All configured notification methods failed, trying original webhook method")
        send_to_webhook(webhook, summary, tech_only)
    
    logger.info("Processing complete")

    # Clean up old data files
    directories_to_clean = [
        "data/raw",      # Raw hotspot data
        "data/filtered", # Filtered hotspot data
        "data/merged",   # Merged data
        "data/inputs",   # LLM input data
        "data/outputs",  # LLM output data
        "data/webhook",  # Webhook logs
        "cache/summary"  # Summary cache
    ]
    days_to_keep = 7 # Set retention period
    logger.info(f"Starting cleanup of data older than {days_to_keep} days...")
    for directory in directories_to_clean:
        cleanup_old_files(directory, days_to_keep=days_to_keep)

    logger.info("Data cleanup complete")

if __name__ == "__main__":
    main()