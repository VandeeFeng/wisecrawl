#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单独的脚本，用于从data/inputs目录读取数据并使用Deepseek进行总结
"""

import os
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
import time

# 导入summary_integration模块
from llm_integration.summary_integration import summarize_with_deepseek

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_latest_input_file(input_dir="data/inputs"):
    """获取inputs目录中最新的输入文件"""
    if not os.path.exists(input_dir):
        logger.error(f"输入目录 {input_dir} 不存在")
        return None
    
    input_files = [f for f in os.listdir(input_dir) if f.startswith("deepseek_input_") and f.endswith(".json")]
    if not input_files:
        logger.error(f"在 {input_dir} 中未找到输入文件")
        return None
    
    # 按修改时间排序，获取最新的文件
    latest_file = max(input_files, key=lambda f: os.path.getmtime(os.path.join(input_dir, f)))
    return os.path.join(input_dir, latest_file)

def process_input_file(file_path, api_key, api_url=None, model_id=None, tech_only=False, max_retries=3):
    """处理单个输入文件并生成摘要"""
    logger.info(f"处理输入文件: {file_path}")
    
    for retry in range(max_retries):
        try:
            logger.info(f"尝试处理 (尝试 {retry+1}/{max_retries})...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 打印输入数据的基本信息以进行调试
            logger.info(f"读取到 {len(data)} 条输入数据")
            if len(data) > 0:
                logger.info(f"第一条数据示例: {json.dumps(data[0], ensure_ascii=False)[:100]}...")
            
            # 确保输入数据格式正确，为每个条目添加必要的字段
            processed_data = []
            for idx, item in enumerate(data):
                # 确保每个条目都有必要的字段
                processed_item = {
                    "id": idx,
                    "title": item.get("title", f"Item {idx}"),
                    "source": item.get("source", "unknown"),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", "#")  # 确保有URL字段
                }
                processed_data.append(processed_item)
            
            # 如果未提供API URL，尝试使用本地Ollama作为备选
            if not api_url:
                logger.info("未提供API URL，尝试使用本地Ollama作为备选")
                api_url = "http://127.0.0.1:11434/v1/chat/completions"
                if not model_id:
                    model_id = "deepseek-r1:14b"
                logger.info(f"使用本地Ollama URL: {api_url}, 模型: {model_id}")
            
            # 调用Deepseek API进行总结
            logger.info(f"开始使用Deepseek进行总结... API URL: {api_url}, Model ID: {model_id}")
            
            # 捕获并输出API密钥的前几个字符以便调试
            masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else '****'
            logger.info(f"使用API密钥(已掩码): {masked_key}")
            
            summary = summarize_with_deepseek(
                processed_data, api_key, api_url, model_id, max_retries=3, tech_only=tech_only
            )
            
            # 打印摘要并返回结果
            logger.info("总结生成完成！")
            print("\n" + "="*50 + "\n")
            print(summary)
            print("\n" + "="*50 + "\n")
            
            return summary
        
        except Exception as e:
            logger.error(f"处理输入文件时出错 (尝试 {retry+1}/{max_retries}): {str(e)}")
            import traceback
            logger.error(traceback.format_exc())  # 打印完整的错误堆栈
            
            if retry < max_retries - 1:
                wait_time = 5 * (retry + 1)  # 递增等待时间
                logger.info(f"将在 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                
                # 如果API URL提供了但是失败了，尝试切换到本地Ollama
                if retry == 1 and api_url and "127.0.0.1" not in api_url:
                    logger.info("尝试切换到本地Ollama作为备选")
                    api_url = "http://127.0.0.1:11434/v1/chat/completions"
                    model_id = "deepseek-r1:14b"
            else:
                logger.error(f"达到最大重试次数 ({max_retries})，放弃处理")
                
                # 尝试保存错误日志
                try:
                    error_dir = os.path.join("data", "errors")
                    os.makedirs(error_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    error_file = os.path.join(error_dir, f"error_{timestamp}.txt")
                    with open(error_file, 'w', encoding='utf-8') as f:
                        f.write(f"处理文件失败: {file_path}\n")
                        f.write(f"错误: {str(e)}\n\n")
                        f.write(traceback.format_exc())
                    logger.info(f"错误日志已保存到: {error_file}")
                except Exception as log_err:
                    logger.error(f"保存错误日志失败: {str(log_err)}")
                
                return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="使用Deepseek总结inputs目录中的数据")
    parser.add_argument("--api-key", help="Deepseek API密钥，不提供则从环境变量DEEPSEEK_API_KEY读取")
    parser.add_argument("--api-url", help="Deepseek API URL，不提供则使用默认值")
    parser.add_argument("--model-id", help="Deepseek模型ID，不提供则使用默认值")
    parser.add_argument("--input-file", help="指定输入文件路径，不提供则使用最新的输入文件")
    parser.add_argument("--tech-only", action="store_true", help="是否只关注科技新闻")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数")
    
    args = parser.parse_args()
    
    # 获取API密钥
    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("未提供Deepseek API密钥，请通过--api-key参数提供或在环境变量DEEPSEEK_API_KEY中设置")
        return 1
    
    # 检查API URL
    api_url = args.api_url
    if not api_url:
        logger.warning("未提供API URL，将使用模块默认值")
    
    # 获取输入文件
    input_file = args.input_file or get_latest_input_file()
    if not input_file:
        logger.error("未找到输入文件")
        return 1
    
    # 处理输入文件
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