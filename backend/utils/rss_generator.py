import logging
import os
from datetime import datetime
from email.utils import formatdate # For RFC 822 date format
import html # To escape characters in XML
from dateutil import parser as date_parser # For flexible date parsing
import json

# Import the config variable
from config.config import RSS_FEED_LINK

logger = logging.getLogger(__name__)

def generate_rss_feed(news_items, output_path, feed_title="WiseCrawl Aggregated News", feed_link=RSS_FEED_LINK, feed_description="Latest news aggregated by WiseCrawl"):
    """
    Generates an RSS 2.0 feed from a list of news items and saves it to a file.

    Args:
        news_items (list): A list of dictionaries, where each dict represents a news item.
                           Expected keys: 'title', 'url', 'summary', 'timestamp' (Unix ms) or 'published'/'extracted_time'.
        output_path (str): The full path where the RSS XML file should be saved.
        feed_title (str): The title of the RSS feed.
        feed_link (str): The URL of the website associated with the feed.
        feed_description (str): A short description of the RSS feed.
    """
    logger.info(f"Starting RSS feed generation for {len(news_items)} items...")

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create directory {output_dir}: {e}")
        return

    # Start XML content
    xml_content = []
    xml_content.append('<?xml version="1.0" encoding="UTF-8" ?>')
    xml_content.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    xml_content.append('  <channel>')
    xml_content.append(f'    <title>{html.escape(feed_title)}</title>')
    xml_content.append(f'    <link>{html.escape(feed_link)}</link>')
    xml_content.append(f'    <description>{html.escape(feed_description)}</description>')
    xml_content.append('    <language>en-us</language>')
    xml_content.append(f'    <lastBuildDate>{formatdate(localtime=True)}</lastBuildDate>')
    xml_content.append(f'    <atom:link href="{html.escape(feed_link)}/rss.xml" rel="self" type="application/rss+xml" />') # Atom link

    for item in news_items:
        title = item.get('title', 'No Title')
        link = item.get('url', '#')
        description = item.get('summary', 'No Description Available')
        guid = link

        pub_date_str = ""
        try:
            timestamp_ms = item.get('timestamp')
            published_str = item.get('published')
            extracted_time_str = item.get('extracted_time')

            dt = None
            if timestamp_ms:
                dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
            elif published_str:
                 try:
                     dt = datetime.strptime(published_str, "%Y-%m-%d %H:%M:%S")
                 except ValueError:
                     logger.warning(f"Could not parse published_str '{published_str}' for '{title}'. Trying dateutil parser.")
                     try:
                         dt = date_parser.parse(published_str)
                     except Exception as e_parse:
                         logger.warning(f"dateutil failed to parse '{published_str}': {e_parse}")
            elif extracted_time_str:
                 try:
                    dt = datetime.fromisoformat(extracted_time_str.replace('Z', '+00:00'))
                 except ValueError:
                    logger.warning(f"Could not parse extracted_time_str '{extracted_time_str}' for '{title}'.")

            if dt:
                pub_date_str = formatdate(dt.timestamp(), localtime=True)
            else:
                 logger.warning(f"Missing valid date for item: '{title}'.")

        except Exception as e:
            logger.error(f"Error processing date for item '{title}': {e}")

        # Escape content
        escaped_title = html.escape(title)
        escaped_link = html.escape(link)
        escaped_description = html.escape(description)
        escaped_guid = html.escape(guid)

        # Append item XML
        xml_content.append('    <item>')
        xml_content.append(f'      <title>{escaped_title}</title>')
        xml_content.append(f'      <link>{escaped_link}</link>')
        xml_content.append(f'      <description>{escaped_description}</description>')
        if pub_date_str:
            xml_content.append(f'      <pubDate>{pub_date_str}</pubDate>')
        xml_content.append(f'      <guid isPermaLink="true">{escaped_guid}</guid>')
        xml_content.append('    </item>')

    # Close channel and rss tags
    xml_content.append('  </channel>')
    xml_content.append('</rss>')

    # Join lines and write to file
    final_xml = '\n'.join(xml_content)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_xml)
        logger.info(f"Successfully generated RSS feed at: {output_path}")
    except IOError as e:
        logger.error(f"Failed to write RSS feed to {output_path}: {e}") 