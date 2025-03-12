#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试Deepseek API超时情况的脚本
"""

import os
import json
import time
import logging
import argparse
import requests
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试数据 - 模拟热点数据
TEST_HOTSPOTS = [
    {
        "title": "测试新闻标题1",
        "url": "https://example.com/news1",
        "source": "test_source",
        "summary": "这是一条测试新闻的摘要内容。"
    },
    {
        "title": "测试新闻标题2",
        "url": "https://example.com/news2",
        "source": "test_source",
        "summary": "这是另一条测试新闻的摘要内容。"
    }
]

# 模拟SOURCE_NAME_MAP
SOURCE_NAME_MAP = {
    "test_source": "测试来源"
}

def test_deepseek_timeout(api_key, api_url=None, model_id=None, timeout_seconds=60, 
                         max_retries=3, retry_delay=5, tech_only=False):
    """
    测试Deepseek API的超时情况
    
    参数:
        api_key (str): Deepseek API密钥
        api_url (str, optional): API URL，默认为None
        model_id (str, optional): 模型ID，默认为None
        timeout_seconds (int, optional): 超时时间（秒），默认为60
        max_retries (int, optional): 最大重试次数，默认为3
        retry_delay (int, optional): 重试间隔（秒），默认为5
        tech_only (bool, optional): 是否只返回科技新闻，默认为False
    
    返回:
        dict: 测试结果，包含成功/失败状态和详细信息
    """
    if api_url is None:
        api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    if model_id is None:
        model_id = "ep-20250307234946-b2znq"
    
    # 记录测试开始时间
    start_time = time.time()
    
    # 初始化结果字典
    result = {
        "success": False,
        "total_time": 0,
        "attempts": 0,
        "error": None,
        "response": None
    }
    
    retry_count = 0
    while retry_count < max_retries:
        attempt_start = time.time()
        result["attempts"] += 1
        
        try:
            logger.info(f"测试 #{retry_count + 1}: 开始调用 Deepseek API (超时设置: {timeout_seconds}秒)")
            
            # 简化输入数据，只传递必要信息
            simplified_hotspots = []
            for idx, item in enumerate(TEST_HOTSPOTS):
                source_name = SOURCE_NAME_MAP.get(item['source'], item['source'])
                simplified_hotspots.append({
                    "id": idx,
                    "title": item['title'],
                    "source": source_name,
                    "summary": item.get('summary', '')
                })
            
            # 转换为JSON格式的输入
            hotspot_json = json.dumps(simplified_hotspots, ensure_ascii=False)
            
            # 根据tech_only参数选择不同的prompt
            if tech_only:
                prompt = f"""
                以下是今日科技热点新闻列表（JSON格式），每个来源均已按照热榜排序，部分新闻包含内容摘要：
                {hotspot_json}
                请总结出10条最重要的科技新闻，优先选择AI相关新闻，去除重复和无关内容。
                
                请以JSON格式返回结果，格式如下：
                ```json
                [
                  {{
                    "title": "新闻标题",
                    "related_ids": [相关新闻的ID列表]
                  }},
                  ...
                ]
                ```
                
                只返回JSON数据，不要有任何额外说明。
                """
            else:
                prompt = f"""
                以下是今日热点新闻列表（JSON格式），每个来源均已按照热榜排序，部分新闻包含内容摘要：
                {hotspot_json}
                请总结出10条最重要的热点新闻，优先选择科技和AI相关新闻。
                
                请以JSON格式返回结果，格式如下：
                ```json
                [
                  {{
                    "title": "新闻标题",
                    "related_ids": [相关新闻的ID列表]
                  }},
                  ...
                ]
                ```
                
                只返回JSON数据，不要有任何额外说明。
                """
            
            # 调用Deepseek API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "你是一个专业的新闻编辑助手，擅长归纳总结热点新闻。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            # 发送请求并计时
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=timeout_seconds  # 使用传入的超时参数
            )
            
            # 检查响应状态
            response.raise_for_status()
            api_result = response.json()
            
            # 计算本次尝试的耗时
            attempt_time = time.time() - attempt_start
            logger.info(f"测试 #{retry_count + 1}: 成功! 耗时: {attempt_time:.2f}秒")
            
            # 更新结果
            result["success"] = True
            result["response"] = api_result
            result["last_attempt_time"] = attempt_time
            break  # 成功则退出循环
            
        except requests.exceptions.Timeout:
            # 超时异常
            attempt_time = time.time() - attempt_start
            logger.warning(f"测试 #{retry_count + 1}: 请求超时! 耗时: {attempt_time:.2f}秒")
            result["error"] = "TIMEOUT"
            result["last_attempt_time"] = attempt_time
            
        except requests.exceptions.ConnectionError as e:
            # 连接错误
            attempt_time = time.time() - attempt_start
            logger.error(f"测试 #{retry_count + 1}: 连接错误! 耗时: {attempt_time:.2f}秒, 错误: {str(e)}")
            result["error"] = f"CONNECTION_ERROR: {str(e)}"
            result["last_attempt_time"] = attempt_time
            
        except requests.exceptions.RequestException as e:
            # 其他请求异常
            attempt_time = time.time() - attempt_start
            logger.error(f"测试 #{retry_count + 1}: 请求异常! 耗时: {attempt_time:.2f}秒, 错误: {str(e)}")
            result["error"] = f"REQUEST_ERROR: {str(e)}"
            result["last_attempt_time"] = attempt_time
            
        except Exception as e:
            # 其他未预期的异常
            attempt_time = time.time() - attempt_start
            logger.error(f"测试 #{retry_count + 1}: 未知错误! 耗时: {attempt_time:.2f}秒, 错误: {str(e)}")
            result["error"] = f"UNKNOWN_ERROR: {str(e)}"
            result["last_attempt_time"] = attempt_time
        
        # 增加重试计数
        retry_count += 1
        
        # 如果还有重试机会，则等待后重试
        if retry_count < max_retries:
            logger.info(f"将在 {retry_delay} 秒后进行第 {retry_count + 1} 次重试...")
            time.sleep(retry_delay)
    
    # 计算总耗时
    result["total_time"] = time.time() - start_time
    
    # 记录最终结果
    if result["success"]:
        logger.info(f"测试成功完成! 总耗时: {result['total_time']:.2f}秒, 尝试次数: {result['attempts']}")
    else:
        logger.warning(f"测试失败! 总耗时: {result['total_time']:.2f}秒, 尝试次数: {result['attempts']}, 错误: {result['error']}")
    
    return result

def save_test_result(result, output_dir="data/tests"):
    """
    保存测试结果到文件
    """
    try:
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        status = "success" if result["success"] else "failed"
        filename = os.path.join(output_dir, f"deepseek_test_{status}_{timestamp}.json")
        
        # 保存结果
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试结果已保存至: {filename}")
        return filename
    except Exception as e:
        logger.error(f"保存测试结果时出错: {str(e)}")
        return None

def main():
    """
    主函数，处理命令行参数并执行测试
    """
    parser = argparse.ArgumentParser(description="测试Deepseek API的超时情况")
    parser.add_argument("--api-key", required=True, help="Deepseek API密钥")
    parser.add_argument("--api-url", default=None, help="API URL，默认使用配置中的URL")
    parser.add_argument("--model-id", default=None, help="模型ID，默认使用配置中的模型ID")
    parser.add_argument("--timeout", type=int, default=60, help="超时时间（秒），默认为60")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数，默认为3")
    parser.add_argument("--retry-delay", type=int, default=5, help="重试间隔（秒），默认为5")
    parser.add_argument("--tech-only", action="store_true", help="是否只返回科技新闻")
    parser.add_argument("--output-dir", default="data/tests", help="测试结果输出目录，默认为data/tests")
    
    args = parser.parse_args()
    
    logger.info("开始测试Deepseek API超时情况...")
    logger.info(f"参数: 超时={args.timeout}秒, 最大重试次数={args.max_retries}, 重试间隔={args.retry_delay}秒")
    
    # 执行测试
    result = test_deepseek_timeout(
        api_key=args.api_key,
        api_url=args.api_url,
        model_id=args.model_id,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        tech_only=args.tech_only
    )
    
    # 保存测试结果
    save_test_result(result, args.output_dir)
    
    # 返回退出码
    return 0 if result["success"] else 1

if __name__ == "__main__":
    exit(main())