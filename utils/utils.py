#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工具函数：各种用到的工具函数
"""

import os
import hashlib
import pickle
import json
import logging
from pathlib import Path
from datetime import datetime
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_hotspots_to_jsonl(hotspots, directory="data"):
    """
    将热点数据保存为JSONL格式，按日期组织，使用绝对路径
    """
    try:
        # 获取当前脚本所在目录的绝对路径
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 构建绝对路径
        abs_directory = os.path.join(script_dir, directory)
        # 确保目录存在
        os.makedirs(abs_directory, exist_ok=True)
        
        # 生成文件名，使用当前日期
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H-%M-%S")
        filename = os.path.join(abs_directory, f"hotspots_{today}_{timestamp}.jsonl")
        
        # 写入JSONL文件
        with open(filename, 'w', encoding='utf-8') as f:
            for item in hotspots:
                # 添加时间戳
                item_with_timestamp = item.copy()
                item_with_timestamp['saved_at'] = datetime.now().isoformat()
                f.write(json.dumps(item_with_timestamp, ensure_ascii=False) + '\n')
        
        logger.info(f"已将 {len(hotspots)} 条热点数据保存至 {filename}")
        return filename
    except Exception as e:
        logger.error(f"保存热点数据时发生错误: {str(e)}")
        return None

def get_content_hash(content):
    """
    计算内容的哈希值，用于缓存标识
    """
    if not content:
        return None
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_summary_cache(cache_dir="cache/summary"):
    """
    加载摘要缓存
    """
    try:
        # 获取当前脚本所在目录的绝对路径
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 构建绝对路径
        abs_cache_dir = os.path.join(script_dir, cache_dir)
        cache_path = Path(abs_cache_dir) / "summary_cache.pkl"
        if not cache_path.exists():
            return {}
        
        with open(cache_path, 'rb') as f:
            cache = pickle.load(f)
            logger.info(f"已加载摘要缓存，包含 {len(cache)} 条记录")
            return cache
    except Exception as e:
        logger.warning(f"加载摘要缓存失败: {str(e)}")
        return {}

def save_summary_cache(cache, cache_dir="cache/summary"):
    """
    保存摘要缓存
    """
    try:
        # 获取当前脚本所在目录的绝对路径
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 构建绝对路径
        abs_cache_dir = os.path.join(script_dir, cache_dir)
        cache_path = Path(abs_cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        with open(cache_path / "summary_cache.pkl", 'wb') as f:
            pickle.dump(cache, f)
            logger.info(f"已保存摘要缓存，共 {len(cache)} 条记录")
    except Exception as e:
        logger.warning(f"保存摘要缓存失败: {str(e)}")

def check_base_url(base_url):
    """
    检查 BASE_URL 是否可访问
    """
    import requests
    try:
        response = requests.get(f"{base_url}/bilibili?limit=5", timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 200:
            logger.info(f"BASE_URL 检查通过: {base_url}")
            return True
        else:
            logger.error(f"BASE_URL 返回错误: {data}")
            return False
    except Exception as e:
        logger.error(f"BASE_URL 检查失败: {str(e)}")
        return False

def format_title_for_display(title, source, max_length=30):
    """
    格式化标题，确保长度一致，适配手机宽度
    """
    # 如果来源包含公众号标识，去掉前缀
    if source.startswith("公众号-"):
        source = source[4:]
    
    # 计算标题最大长度（考虑到后面要加上来源）
    source_part = f" - {source}"
    title_max_length = max_length - len(source_part)
    
    # 如果标题太长，截断并添加省略号
    if len(title) > title_max_length:
        title = title[:title_max_length-1] + "…"
    
    # 返回格式化后的标题
    return f"{title}{source_part}"

def cleanup_old_files(directory, days_to_keep=7):
    """
    清理指定目录下超过指定天数的旧文件。

    参数:
        directory (str): 需要清理的目录路径 (相对于项目根目录)。
        days_to_keep (int): 文件保留的最长天数，默认为7天。
    """
    try:
        # 获取当前脚本所在目录的绝对路径
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 构建要清理目录的绝对路径
        abs_directory = os.path.join(script_dir, directory)

        if not os.path.isdir(abs_directory):
            logger.warning(f"清理目录不存在，跳过清理: {abs_directory}")
            return

        logger.info(f"开始清理目录 '{abs_directory}' 中超过 {days_to_keep} 天的旧文件...")

        # 计算截止时间戳
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        deleted_count = 0

        # 遍历目录中的所有文件
        for filename in os.listdir(abs_directory):
            file_path = os.path.join(abs_directory, filename)
            # 确保是文件而不是子目录
            if os.path.isfile(file_path):
                try:
                    # 获取文件的最后修改时间
                    file_mtime = os.path.getmtime(file_path)
                    # 如果文件的修改时间早于截止时间，则删除
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"已删除旧文件: {file_path}")
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"删除文件 {file_path} 时出错: {str(e)}")

        logger.info(f"目录 '{abs_directory}' 清理完成，共删除 {deleted_count} 个旧文件。")

    except Exception as e:
        logger.error(f"清理目录 {directory} 时发生意外错误: {str(e)}")