import os
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
import time

# Import summary_integration module
from llm_integration.summary_integration import summarize_with_deepseek

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_latest_input_file(input_dir="data/inputs"):
    """Get the latest input file from the inputs directory"""
    if not os.path.exists(input_dir):
        logger.error(f"Input directory {input_dir} does not exist")
        return None
    
    input_files = [f for f in os.listdir(input_dir) if f.startswith("deepseek_input_") and f.endswith(".json")]
    if not input_files:
        logger.error(f"No input files found in {input_dir}")
        return None
    
    # Sort by modification time, get the latest file
    latest_file = max(input_files, key=lambda f: os.path.getmtime(os.path.join(input_dir, f)))
    return os.path.join(input_dir, latest_file)

def process_input_file(file_path, api_key, api_url=None, model_id=None, tech_only=False, max_retries=3):
    """Process a single input file and generate a summary"""
    logger.info(f"Processing input file: {file_path}")
    
    for retry in range(max_retries):
        try:
            logger.info(f"Attempting to process (attempt {retry+1}/{max_retries})...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Print basic information about the input data for debugging
            logger.info(f"Read {len(data)} input items")
            if len(data) > 0:
                logger.info(f"First data example: {json.dumps(data[0], ensure_ascii=False)[:100]}...")
            
            # Ensure input data format is correct, add necessary fields for each entry
            processed_data = []
            for idx, item in enumerate(data):
                # Ensure each item has necessary fields
                processed_item = {
                    "id": idx,
                    "title": item.get("title", f"Item {idx}"),
                    "source": item.get("source", "unknown"),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", "#")  # Ensure URL field exists
                }
                processed_data.append(processed_item)
            
            # If API URL is not provided, try using local Ollama as fallback
            if not api_url:
                logger.info("API URL not provided, trying local Ollama as fallback")
                api_url = "http://127.0.0.1:11434/v1/chat/completions"
                if not model_id:
                    model_id = "deepseek-r1:14b"
                logger.info(f"Using local Ollama URL: {api_url}, model: {model_id}")
            
            # Call Deepseek API for summarization
            logger.info(f"Starting summarization with Deepseek... API URL: {api_url}, Model ID: {model_id}")
            
            # Capture and output the first few characters of the API key for debugging
            masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else '****'
            logger.info(f"Using API key (masked): {masked_key}")
            
            summary = summarize_with_deepseek(
                processed_data, api_key, api_url, model_id, max_retries=3, tech_only=tech_only
            )
            
            # Print summary and return result
            logger.info("Summary generation completed!")
            print("\n" + "="*50 + "\n")
            print(summary)
            print("\n" + "="*50 + "\n")
            
            return summary
        
        except Exception as e:
            logger.error(f"Error processing input file (attempt {retry+1}/{max_retries}): {str(e)}")
            import traceback
            logger.error(traceback.format_exc())  # Print full error stack trace
            
            if retry < max_retries - 1:
                wait_time = 5 * (retry + 1)  # Incremental wait time
                logger.info(f"Will retry in {wait_time} seconds...")
                time.sleep(wait_time)
                
                # If API URL was provided but failed, try switching to local Ollama
                if retry == 1 and api_url and "127.0.0.1" not in api_url:
                    logger.info("Trying to switch to local Ollama as fallback")
                    api_url = "http://127.0.0.1:11434/v1/chat/completions"
                    model_id = "deepseek-r1:14b"
            else:
                logger.error(f"Maximum retry attempts reached ({max_retries}), giving up")
                
                # Try to save error log
                try:
                    error_dir = os.path.join("data", "errors")
                    os.makedirs(error_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    error_file = os.path.join(error_dir, f"error_{timestamp}.txt")
                    with open(error_file, 'w', encoding='utf-8') as f:
                        f.write(f"Failed to process file: {file_path}\n")
                        f.write(f"Error: {str(e)}\n\n")
                        f.write(traceback.format_exc())
                    logger.info(f"Error log saved to: {error_file}")
                except Exception as log_err:
                    logger.error(f"Failed to save error log: {str(log_err)}")
                
                return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Summarize data from the inputs directory using Deepseek")
    parser.add_argument("--api-key", help="Deepseek API key, if not provided will read from DEEPSEEK_API_KEY environment variable")
    parser.add_argument("--api-url", help="Deepseek API URL, uses default if not provided")
    parser.add_argument("--model-id", help="Deepseek model ID, uses default if not provided")
    parser.add_argument("--input-file", help="Specify input file path, uses the latest input file if not provided")
    parser.add_argument("--tech-only", action="store_true", help="Whether to focus only on tech news")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of retry attempts")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("Deepseek API key not provided, please provide it via --api-key parameter or set in DEEPSEEK_API_KEY environment variable")
        return 1
    
    # Check API URL
    api_url = args.api_url
    if not api_url:
        logger.warning("API URL not provided, will use module default")
    
    # Get input file
    input_file = args.input_file or get_latest_input_file()
    if not input_file:
        logger.error("No input file found")
        return 1
    
    # Process input file
    process_input_file(
        input_file,
        api_key,
        args.api_url,
        args.model_id,
        args.tech_only,
        args.max_retries
    )
    
    return 0

if __name__ == "__main__":
    exit(main()) 