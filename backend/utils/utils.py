import os
import hashlib
import pickle
import json
import logging
from pathlib import Path
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_project_root():
    """
    Get the project root directory (one level up from backend directory)
    """
    # Get the backend directory (parent of utils)
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Get the project root (parent of backend)
    return os.path.dirname(backend_dir)

def get_backend_dir():
    """
    Get the backend directory
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def save_hotspots_to_jsonl(hotspots, directory="data"):
    """
    Save hotspot data in JSONL format, organized by date, using absolute path from project root
    """
    try:
        # Get project root directory
        project_root = get_project_root()
        # Build absolute path from project root
        abs_directory = os.path.join(project_root, directory)
        # Ensure directory exists
        os.makedirs(abs_directory, exist_ok=True)
        
        # Generate filename with current date
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H-%M-%S")
        filename = os.path.join(abs_directory, f"hotspots_{today}_{timestamp}.jsonl")
        
        # Write to JSONL file
        with open(filename, 'w', encoding='utf-8') as f:
            for item in hotspots:
                # Add timestamp
                item_with_timestamp = item.copy()
                item_with_timestamp['saved_at'] = datetime.now().isoformat()
                f.write(json.dumps(item_with_timestamp, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved {len(hotspots)} hotspot items to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving hotspot data: {str(e)}")
        return None

def get_content_hash(content):
    """
    Calculate content hash for cache identification
    """
    if not content:
        return None
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_summary_cache(cache_dir="cache/summary"):
    """
    Load summary cache from backend directory
    """
    try:
        # Get backend directory
        backend_dir = get_backend_dir()
        # Build absolute path from backend directory
        abs_cache_dir = os.path.join(backend_dir, cache_dir)
        cache_path = Path(abs_cache_dir) / "summary_cache.pkl"
        if not cache_path.exists():
            return {}
        
        with open(cache_path, 'rb') as f:
            cache = pickle.load(f)
            logger.info(f"Loaded summary cache with {len(cache)} entries")
            return cache
    except Exception as e:
        logger.warning(f"Failed to load summary cache: {str(e)}")
        return {}

def save_summary_cache(cache, cache_dir="cache/summary"):
    """
    Save summary cache in backend directory
    """
    try:
        # Get backend directory
        backend_dir = get_backend_dir()
        # Build absolute path from backend directory
        abs_cache_dir = os.path.join(backend_dir, cache_dir)
        cache_path = Path(abs_cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        with open(cache_path / "summary_cache.pkl", 'wb') as f:
            pickle.dump(cache, f)
            logger.info(f"Saved summary cache with {len(cache)} entries")
    except Exception as e:
        logger.warning(f"Failed to save summary cache: {str(e)}")

def check_base_url(base_url):
    """
    Check if BASE_URL is accessible
    """
    import requests
    try:
        response = requests.get(f"{base_url}/sspai?limit=5", timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 200:
            logger.info(f"BASE_URL check passed: {base_url}")
            return True
        else:
            logger.error(f"BASE_URL returned error: {data}")
            return False
    except Exception as e:
        logger.error(f"BASE_URL check failed: {str(e)}")
        return False

def format_title_for_display(title, source, max_length=30):
    """
    Format title for display, ensure consistent length for mobile width
    """
    # Remove prefix if source contains WeChat Official Account identifier
    if source.startswith("公众号-"):
        source = source[4:]
    
    # Calculate max title length (considering source will be added)
    source_part = f" - {source}"
    title_max_length = max_length - len(source_part)
    
    # If title is too long, truncate and add ellipsis
    if len(title) > title_max_length:
        title = title[:title_max_length-1] + "…"
    
    # Return formatted title
    return f"{title}{source_part}"

def cleanup_old_files(directory, days_to_keep=7, use_backend_dir=False):
    """
    Clean up old files in specified directory that are older than specified days.

    Args:
        directory (str): Directory path to clean (relative to project root or backend dir).
        days_to_keep (int): Number of days to keep files, default is 7 days.
        use_backend_dir (bool): If True, use backend directory as base, otherwise use project root.
    """
    try:
        # Get base directory (project root or backend)
        base_dir = get_backend_dir() if use_backend_dir else get_project_root()
        # Build absolute path from base directory
        abs_directory = os.path.join(base_dir, directory)

        if not os.path.isdir(abs_directory):
            logger.warning(f"Directory does not exist, skipping cleanup: {abs_directory}")
            return

        logger.info(f"Starting cleanup of files older than {days_to_keep} days in '{abs_directory}'...")

        # Calculate cutoff timestamp
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        deleted_count = 0

        # Iterate through all files in directory
        for filename in os.listdir(abs_directory):
            file_path = os.path.join(abs_directory, filename)
            # Ensure it's a file not a subdirectory
            if os.path.isfile(file_path):
                try:
                    # Get file's last modification time
                    file_mtime = os.path.getmtime(file_path)
                    # Delete if file is older than cutoff time
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"Deleted old file: {file_path}")
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {str(e)}")

        logger.info(f"Cleanup complete for '{abs_directory}', deleted {deleted_count} old files.")

    except Exception as e:
        logger.error(f"Error cleaning up directory {directory}: {str(e)}")