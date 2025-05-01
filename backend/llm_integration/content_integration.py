import json
import logging
import time
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from utils.utils import get_content_hash, load_summary_cache, save_summary_cache
from utils.token_tracker import token_tracker
from config.config import CONTENT_MODEL_ID

logger = logging.getLogger(__name__)

def summarize_with_tencent_hunyuan(content, api_key, title="", max_retries=3, use_cache=True):
    """
    使用腾讯混元turbo-S模型对内容进行概述总结
    返回JSON格式，包含摘要和科技相关性判断
    支持缓存机制，避免重复处理相同内容
    """
    if not content or len(content.strip()) < 50:
        logger.warning(f"内容过短或为空，跳过摘要生成: {content[:50]}...")
        return {"summary": "", "is_tech": False}
    
    content_hash = get_content_hash(content[:2000])  # 只对前2000字符计算哈希
    
    if use_cache and content_hash:
        # 加载缓存
        summary_cache = load_summary_cache()
        
        if content_hash in summary_cache:
            cached_result = summary_cache[content_hash]
            logger.info(f"从缓存中获取摘要: {cached_result['summary'][:30]}...")
            return cached_result
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            logger.info(f"发送至内容处理模型的内容长度: {len(content[:2000])} 字符")
            
            llm = ChatOpenAI(
                model=CONTENT_MODEL_ID,  
                temperature=0.3,
                api_key='ollama',
                # max_tokens=150,
                base_url="http://127.0.0.1:11434/v1/"  
            )
            
            prompt = PromptTemplate(
                input_variables=["content", "title"],
                template="""请对以下新闻内容进行简洁概述，并判断是否与科技相关（包括AI、人工智能、互联网、软件、硬件、电子产品等）。请优先通过新闻标题来判断是否与科技相关，如果标题中没有科技相关的关键词，请通过新闻内容来判断。
                    
                    新闻标题：{title}
                    新闻内容：
                    {content}
                    
                    请以JSON格式返回，包含以下字段：
                    1. summary: 新闻摘要，不超过150个字
                    2. is_tech: 布尔值，表示是否与科技相关

                    只返回JSON格式，不要有任何额外说明。
                    /no_think
                    """
            )
            
            chain = LLMChain(llm=llm, prompt=prompt)
            
            response = chain.invoke({"content": content[:2000], "title": title})  # 限制输入长度
            
            result_text = response.get("text", "").strip()
            
            try:
                if not result_text.startswith("{"):
                    import re
                    json_match = re.search(r'({.*})', result_text, re.DOTALL)
                    if json_match:
                        result_text = json_match.group(1)
                
                result = json.loads(result_text)
                
                if "summary" not in result:
                    result["summary"] = ""
                if "is_tech" not in result:
                    result["is_tech"] = False
                
                # Track token usage for content model
                token_tracker.add_usage(
                    CONTENT_MODEL_ID,
                    prompt_tokens=len(content[:2000]) // 4,  # Rough estimate
                    completion_tokens=len(result_text) // 4   # Rough estimate
                )
                
                logger.info(f"生成的摘要: {result['summary']}, 科技相关: {result['is_tech']}")
                
                if use_cache and content_hash:
                    summary_cache = load_summary_cache()
                    summary_cache[content_hash] = result
                    save_summary_cache(summary_cache)
                
                return result
            except json.JSONDecodeError:
                logger.warning(f"JSON解析失败，使用原始文本: {result_text}")
                result = {"summary": result_text[:80], "is_tech": False}
                
                if use_cache and content_hash:
                    summary_cache = load_summary_cache()
                    summary_cache[content_hash] = result
                    save_summary_cache(summary_cache)
                
                return result
        
        except Exception as e:
            logger.error(f"调用内容处理模型失败: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"5秒后重试 ({retry_count}/{max_retries})...")
                time.sleep(5)
            else:
                break
    
    return {"summary": "", "is_tech": False}
