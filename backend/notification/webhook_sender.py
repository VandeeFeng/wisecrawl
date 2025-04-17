import os
import json
import logging
import requests
import base64
import hashlib
import hmac
import time
import urllib.parse
import re
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 推送配置，从环境变量中读取
push_config = {
    # 全局开关，控制是否启用消息推送
    'PUSH_ENABLED': False,  # 默认关闭推送功能
    
    # 企业微信机器人
    'QYWX_KEY': '',  # 企业微信机器人的 webhook key
    'QYWX_ORIGIN': '',  # 企业微信代理地址，默认为 https://qyapi.weixin.qq.com
    
    # 钉钉机器人
    'DD_BOT_SECRET': '',  # 钉钉机器人的 DD_BOT_SECRET
    'DD_BOT_TOKEN': '',  # 钉钉机器人的 DD_BOT_TOKEN
    
    # 飞书机器人
    'FSKEY': '',  # 飞书机器人的 FSKEY
    
    # 企业微信应用
    'QYWX_AM': '',  # 企业微信应用参数，格式为：corpid,corpsecret,touser,agentid,media_id
    
    # Telegram机器人
    'TG_BOT_TOKEN': '',  # Telegram机器人的 token
    'TG_USER_ID': '',  # Telegram用户ID
    'TG_API_HOST': '',  # Telegram API代理地址
    'TG_PROXY_HOST': '',  # Telegram代理地址
    'TG_PROXY_PORT': '',  # Telegram代理端口
    'TG_PROXY_AUTH': '',  # Telegram代理认证信息
    
    # Bark
    'BARK_PUSH': '',  # Bark推送URL
    'BARK_SOUND': '',  # Bark推送声音
    'BARK_GROUP': '',  # Bark推送分组
    
    # PushPlus
    'PUSH_PLUS_TOKEN': '',  # PushPlus Token
    'PUSH_PLUS_USER': '',  # PushPlus 群组编码
    
    # Server酱
    'PUSH_KEY': '',  # Server酱 PUSH_KEY
    
    # 原始Webhook URL
    'WEBHOOK_URL': '',  # 原始Webhook URL，用于兼容旧版本
}

# 从环境变量中读取配置
for k in push_config:
    if os.getenv(k):
        push_config[k] = os.getenv(k)

# 格式化内容，添加标题和页脚
def format_content(content, is_tech_only=False):
    """
    格式化内容，添加标题和页脚
    """
    # 获取当前日期和时间
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    # 根据是否只包含科技热点来设置标题
    title_prefix = "科技热点" if is_tech_only else "热点新闻"
    
    # 添加标题和查看全部热点的链接
    header = f"# {today} {current_time} {title_prefix}早报\n\n"
    footer = f"\n\n[查看全部热点](https://hot.tuber.cc/)"
    
    # 构建markdown格式的内容
    markdown_content = header + content + footer
    
    return {
        "title": f"{today} {current_time} {title_prefix}早报",
        "content": markdown_content,
        "plain_content": f"{today} {current_time} {title_prefix}早报\n\n{content}\n\n查看全部热点: https://hot.tuber.cc/",
        "timestamp": now.strftime("%H-%M-%S"),
        "today": today
    }

# 保存发送内容和响应
def save_content_and_response(formatted_content, request_data=None, response_data=None, response=None, push_type="webhook"):
    """
    Save webhook content and response data to files
    """
    # 检查对应的推送方式是否启用
    if push_type == "webhook" and not push_config.get("WEBHOOK_URL"):
        return
    elif push_type == "wecom_bot" and not push_config.get("QYWX_KEY"):
        return
    elif push_type == "dingding_bot" and (not push_config.get("DD_BOT_TOKEN") or not push_config.get("DD_BOT_SECRET")):
        return
    elif push_type == "feishu_bot" and not push_config.get("FSKEY"):
        return
    elif push_type == "telegram_bot" and (not push_config.get("TG_BOT_TOKEN") or not push_config.get("TG_USER_ID")):
        return
    elif push_type == "bark" and not push_config.get("BARK_PUSH"):
        return
    elif push_type == "pushplus_bot" and not push_config.get("PUSH_PLUS_TOKEN"):
        return
    elif push_type == "serverJ" and not push_config.get("PUSH_KEY"):
        return
    elif push_type == "wecom_app" and not push_config.get("QYWX_AM"):
        return
    
    try:
        # Get project root directory (parent of backend)
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_directory = os.path.join(current_dir, "data", "webhook")
        os.makedirs(output_directory, exist_ok=True)
        timestamp = formatted_content["timestamp"]
        today = formatted_content["today"]
        
        # Save content
        content_filename = os.path.join(output_directory, f"{push_type}_content_{today}_{timestamp}.md")
        with open(content_filename, 'w', encoding='utf-8') as f:
            f.write(formatted_content["content"])
        logger.info(f"已保存{push_type}发送内容至 {content_filename}")
        
        # Save request data
        if request_data:
            request_filename = os.path.join(output_directory, f"{push_type}_request_{today}_{timestamp}.json")
            with open(request_filename, 'w', encoding='utf-8') as f:
                json.dump(request_data, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存{push_type}请求数据至 {request_filename}")
        
        # Save response data
        if response or response_data:
            response_filename = os.path.join(output_directory, f"{push_type}_response_{today}_{timestamp}.json")
            if response_data:
                with open(response_filename, 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, ensure_ascii=False, indent=2)
            elif response:
                try:
                    response_json = response.json()
                    with open(response_filename, 'w', encoding='utf-8') as f:
                        json.dump(response_json, f, ensure_ascii=False, indent=2)
                except:
                    with open(response_filename, 'w', encoding='utf-8') as f:
                        f.write(f"Status Code: {response.status_code}\nContent: {response.text}")
            logger.info(f"已保存{push_type}响应至 {response_filename}")
    except Exception as e:
        logger.error(f"Error saving content and response: {str(e)}")
        return None

# 企业微信机器人推送
def wecom_bot(content, is_tech_only=False):
    """
    通过企业微信机器人推送消息
    """
    if not push_config.get("QYWX_KEY"):
        logger.warning("企业微信机器人的 QYWX_KEY 未设置，取消推送")
        return False
    
    try:
        logger.info("企业微信机器人服务启动")
        
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 设置企业微信API地址
        origin = "https://qyapi.weixin.qq.com"
        if push_config.get("QYWX_ORIGIN"):
            origin = push_config.get("QYWX_ORIGIN")
        
        # 构建请求URL和数据
        url = f"{origin}/cgi-bin/webhook/send?key={push_config.get('QYWX_KEY')}"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        
        # 企业微信webhook支持markdown格式
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": formatted_content["content"]
            }
        }
        
        # 保存内容和请求
        save_content_and_response(formatted_content, payload, push_type="wecom_bot")
        
        # 发送请求
        response = requests.post(url=url, data=json.dumps(payload), headers=headers, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 保存响应
        save_content_and_response(formatted_content, None, response_data, push_type="wecom_bot")
        
        if response_data["errcode"] == 0:
            logger.info("企业微信机器人推送成功！")
            return True
        else:
            logger.error(f"企业微信机器人推送失败！错误码：{response_data['errcode']}")
            return False
    except Exception as e:
        logger.error(f"企业微信机器人推送时发生错误: {str(e)}")
        return False

# 钉钉机器人推送
def dingding_bot(content, is_tech_only=False):
    """
    通过钉钉机器人推送消息
    """
    if not push_config.get("DD_BOT_SECRET") or not push_config.get("DD_BOT_TOKEN"):
        logger.warning("钉钉机器人的 DD_BOT_SECRET 或 DD_BOT_TOKEN 未设置，取消推送")
        return False
    
    try:
        logger.info("钉钉机器人服务启动")
        
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 计算签名
        timestamp = str(round(time.time() * 1000))
        secret_enc = push_config.get("DD_BOT_SECRET").encode("utf-8")
        string_to_sign = f"{timestamp}\n{push_config.get('DD_BOT_SECRET')}"
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        
        # 构建请求URL和数据
        url = f'https://oapi.dingtalk.com/robot/send?access_token={push_config.get("DD_BOT_TOKEN")}&timestamp={timestamp}&sign={sign}'
        headers = {"Content-Type": "application/json;charset=utf-8"}
        
        # 钉钉机器人支持markdown格式
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": formatted_content["title"],
                "text": formatted_content["content"]
            }
        }
        
        # 保存内容和请求
        save_content_and_response(formatted_content, payload, push_type="dingding_bot")
        
        # 发送请求
        response = requests.post(url=url, data=json.dumps(payload), headers=headers, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 保存响应
        save_content_and_response(formatted_content, None, response_data, push_type="dingding_bot")
        
        if not response_data["errcode"]:
            logger.info("钉钉机器人推送成功！")
            return True
        else:
            logger.error(f"钉钉机器人推送失败！错误码：{response_data['errcode']}")
            return False
    except Exception as e:
        logger.error(f"钉钉机器人推送时发生错误: {str(e)}")
        return False

# 飞书机器人推送
def feishu_bot(content, is_tech_only=False):
    """
    通过飞书机器人推送消息
    """
    if not push_config.get("FSKEY"):
        logger.warning("飞书机器人的 FSKEY 未设置，取消推送")
        return False
    
    try:
        logger.info("飞书机器人服务启动")
        
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 构建请求URL和数据
        url = f'https://open.feishu.cn/open-apis/bot/v2/hook/{push_config.get("FSKEY")}'
        
        # 飞书机器人支持富文本格式
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": formatted_content["title"],
                        "content": [[{"tag": "text", "text": formatted_content["plain_content"]}]]
                    }
                }
            }
        }
        
        # 保存内容和请求
        save_content_and_response(formatted_content, payload, push_type="feishu_bot")
        
        # 发送请求
        response = requests.post(url=url, json=payload, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 保存响应
        save_content_and_response(formatted_content, None, response_data, push_type="feishu_bot")
        
        if response_data.get("StatusCode") == 0 or response_data.get("code") == 0:
            logger.info("飞书机器人推送成功！")
            return True
        else:
            logger.error(f"飞书机器人推送失败！错误信息：{response_data}")
            return False
    except Exception as e:
        logger.error(f"飞书机器人推送时发生错误: {str(e)}")
        return False

# Telegram机器人推送
def telegram_bot(content, is_tech_only=False):
    """
    通过Telegram机器人推送消息
    """
    if not push_config.get("TG_BOT_TOKEN") or not push_config.get("TG_USER_ID"):
        logger.warning("Telegram机器人的 TG_BOT_TOKEN 或 TG_USER_ID 未设置，取消推送")
        return False
    
    try:
        logger.info("Telegram机器人服务启动")
        
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 设置API地址
        if push_config.get("TG_API_HOST"):
            url = f"https://{push_config.get('TG_API_HOST')}/bot{push_config.get('TG_BOT_TOKEN')}/sendMessage"
        else:
            url = f"https://api.telegram.org/bot{push_config.get('TG_BOT_TOKEN')}/sendMessage"
        
        # 构建请求数据
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "chat_id": str(push_config.get("TG_USER_ID")),
            "text": formatted_content["plain_content"],
            "disable_web_page_preview": "true",
            "parse_mode": "Markdown"
        }
        
        # 设置代理
        proxies = None
        if push_config.get("TG_PROXY_HOST") and push_config.get("TG_PROXY_PORT"):
            if push_config.get("TG_PROXY_AUTH") is not None and "@" not in push_config.get("TG_PROXY_HOST"):
                proxy_host = f"{push_config.get('TG_PROXY_AUTH')}@{push_config.get('TG_PROXY_HOST')}"
            else:
                proxy_host = push_config.get("TG_PROXY_HOST")
            proxyStr = f"http://{proxy_host}:{push_config.get('TG_PROXY_PORT')}"
            proxies = {"http": proxyStr, "https": proxyStr}
        
        # 保存内容和请求
        save_content_and_response(formatted_content, payload, push_type="telegram_bot")
        
        # 发送请求
        response = requests.post(url=url, headers=headers, params=payload, proxies=proxies, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 保存响应
        save_content_and_response(formatted_content, None, response_data, push_type="telegram_bot")
        
        if response_data["ok"]:
            logger.info("Telegram机器人推送成功！")
            return True
        else:
            logger.error(f"Telegram机器人推送失败！错误信息：{response_data}")
            return False
    except Exception as e:
        logger.error(f"Telegram机器人推送时发生错误: {str(e)}")
        return False

# Bark推送
def bark(content, is_tech_only=False):
    """
    通过Bark推送消息
    """
    if not push_config.get("BARK_PUSH"):
        logger.warning("Bark的 BARK_PUSH 未设置，取消推送")
        return False
    
    try:
        logger.info("Bark服务启动")
        
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 构建请求URL
        if push_config.get("BARK_PUSH").startswith("http"):
            url = f'{push_config.get("BARK_PUSH")}/{urllib.parse.quote_plus(formatted_content["title"])}/{urllib.parse.quote_plus(content)}'
        else:
            url = f'https://api.day.app/{push_config.get("BARK_PUSH")}/{urllib.parse.quote_plus(formatted_content["title"])}/{urllib.parse.quote_plus(content)}'
        
        # 添加参数
        params = {}
        if push_config.get("BARK_SOUND"):
            params["sound"] = push_config.get("BARK_SOUND")
        if push_config.get("BARK_GROUP"):
            params["group"] = push_config.get("BARK_GROUP")
        
        # 保存内容和请求
        save_content_and_response(formatted_content, {"url": url, "params": params}, push_type="bark")
        
        # 发送请求
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 保存响应
        save_content_and_response(formatted_content, None, response_data, push_type="bark")
        
        if response_data["code"] == 200:
            logger.info("Bark推送成功！")
            return True
        else:
            logger.error(f"Bark推送失败！错误信息：{response_data}")
            return False
    except Exception as e:
        logger.error(f"Bark推送时发生错误: {str(e)}")
        return False

# PushPlus推送
def pushplus_bot(content, is_tech_only=False):
    """
    通过PushPlus推送消息
    """
    if not push_config.get("PUSH_PLUS_TOKEN"):
        logger.warning("PushPlus的 PUSH_PLUS_TOKEN 未设置，取消推送")
        return False
    
    try:
        logger.info("PushPlus服务启动")
        
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 构建请求数据
        url = "http://www.pushplus.plus/send"
        payload = {
            "token": push_config.get("PUSH_PLUS_TOKEN"),
            "title": formatted_content["title"],
            "content": formatted_content["content"],
            "template": "markdown"
        }
        
        # 添加群组参数
        if push_config.get("PUSH_PLUS_USER"):
            payload["topic"] = push_config.get("PUSH_PLUS_USER")
        
        # 保存内容和请求
        save_content_and_response(formatted_content, payload, push_type="pushplus_bot")
        
        # 发送请求
        headers = {"Content-Type": "application/json"}
        response = requests.post(url=url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 保存响应
        save_content_and_response(formatted_content, None, response_data, push_type="pushplus_bot")
        
        if response_data["code"] == 200:
            logger.info("PushPlus推送成功！")
            return True
        else:
            # 尝试旧版接口
            url_old = "http://pushplus.hxtrip.com/send"
            response_old = requests.post(url=url_old, json=payload, headers=headers, timeout=15)
            response_old.raise_for_status()
            response_data_old = response_old.json()
            
            # 保存旧版接口响应
            save_content_and_response(formatted_content, None, response_data_old, push_type="pushplus_bot_old")
            
            if response_data_old["code"] == 200:
                logger.info("PushPlus(旧版)推送成功！")
                return True
            else:
                logger.error(f"PushPlus推送失败！错误信息：{response_data}")
                return False
    except Exception as e:
        logger.error(f"PushPlus推送时发生错误: {str(e)}")
        return False

# Server酱推送
def serverJ(content, is_tech_only=False):
    """
    通过Server酱推送消息
    """
    if not push_config.get("PUSH_KEY"):
        logger.warning("Server酱的 PUSH_KEY 未设置，取消推送")
        return False
    
    try:
        logger.info("Server酱服务启动")
        
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 构建请求数据
        payload = {
            "text": formatted_content["title"],
            "desp": content.replace("\n", "\n\n")
        }
        
        # 根据PUSH_KEY格式选择不同的URL
        if push_config.get("PUSH_KEY").find("SCT") != -1:
            url = f'https://sctapi.ftqq.com/{push_config.get("PUSH_KEY")}.send'
        else:
            url = f'https://sc.ftqq.com/{push_config.get("PUSH_KEY")}.send'
        
        # 保存内容和请求
        save_content_and_response(formatted_content, {"url": url, "payload": payload}, push_type="serverJ")
        
        # 发送请求
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 保存响应
        save_content_and_response(formatted_content, None, response_data, push_type="serverJ")
        
        if response_data.get("errno") == 0 or response_data.get("code") == 0:
            logger.info("Server酱推送成功！")
            return True
        else:
            logger.error(f"Server酱推送失败！错误信息：{response_data}")
            return False
    except Exception as e:
        logger.error(f"Server酱推送时发生错误: {str(e)}")
        return False

# 企业微信应用推送
def wecom_app(content, is_tech_only=False):
    """
    通过企业微信应用推送消息
    """
    if not push_config.get("QYWX_AM"):
        logger.warning("企业微信应用的 QYWX_AM 未设置，取消推送")
        return False
    
    try:
        logger.info("企业微信应用服务启动")
        
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 解析QYWX_AM参数
        QYWX_AM_AY = re.split(",", push_config.get("QYWX_AM"))
        if len(QYWX_AM_AY) < 4 or len(QYWX_AM_AY) > 5:
            logger.error("QYWX_AM 设置错误，格式应为：corpid,corpsecret,touser,agentid,media_id")
            return False
        
        corpid = QYWX_AM_AY[0]
        corpsecret = QYWX_AM_AY[1]
        touser = QYWX_AM_AY[2]
        agentid = QYWX_AM_AY[3]
        try:
            media_id = QYWX_AM_AY[4]
        except IndexError:
            media_id = ""
        
        # 获取访问令牌
        token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        if push_config.get("QYWX_ORIGIN"):
            token_url = f"{push_config.get('QYWX_ORIGIN')}/cgi-bin/gettoken"
        
        token_params = {
            "corpid": corpid,
            "corpsecret": corpsecret
        }
        token_response = requests.post(token_url, params=token_params, timeout=15)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data["access_token"]
        
        # 构建消息发送请求
        send_url = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
        if push_config.get("QYWX_ORIGIN"):
            send_url = f"{push_config.get('QYWX_ORIGIN')}/cgi-bin/message/send"
        send_url = f"{send_url}?access_token={access_token}"
        
        # 根据是否有media_id选择发送文本消息或图文消息
        if not media_id:
            # 发送文本消息
            message = formatted_content["plain_content"]
            payload = {
                "touser": touser,
                "msgtype": "text",
                "agentid": agentid,
                "text": {"content": message},
                "safe": "0"
            }
        else:
            # 发送图文消息
            payload = {
                "touser": touser,
                "msgtype": "mpnews",
                "agentid": agentid,
                "mpnews": {
                    "articles": [{
                        "title": formatted_content["title"],
                        "thumb_media_id": media_id,
                        "author": "热点推送",
                        "content_source_url": "",
                        "content": content.replace("\n", "<br/>"),
                        "digest": content
                    }]
                }
            }
        
        # 保存内容和请求
        save_content_and_response(formatted_content, payload, push_type="wecom_app")
        
        # 发送请求
        headers = {"Content-Type": "application/json"}
        response = requests.post(send_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 保存响应
        save_content_and_response(formatted_content, None, response_data, push_type="wecom_app")
        
        if response_data["errcode"] == 0:
            logger.info("企业微信应用推送成功！")
            return True
        else:
            logger.error(f"企业微信应用推送失败！错误信息：{response_data}")
            return False
    except Exception as e:
        logger.error(f"企业微信应用推送时发生错误: {str(e)}")
        return False

# 兼容原有的send_to_webhook函数
def send_to_webhook(webhook_url, content, is_tech_only=False):
    """
    将内容发送到webhook（腾讯内部企微机器人）
    保存发送的内容到文件
    兼容原有的调用方式
    """
    try:
        # 格式化内容
        formatted_content = format_content(content, is_tech_only)
        
        # 企业微信webhook格式
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": formatted_content["content"]
            }
        }
        
        # 保存内容和请求
        save_content_and_response(formatted_content, payload, push_type="webhook")
        
        # 发送请求
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        # 保存响应
        save_content_and_response(formatted_content, None, None, response, push_type="webhook")
        
        logger.info(f"成功推送{formatted_content['title']}到webhook")
        return True
    except Exception as e:
        logger.error(f"推送到webhook时发生错误: {str(e)}")
        return False

# 主函数：根据配置选择推送方式
def notify(content, is_tech_only=False):
    """
    根据环境变量配置选择推送方式
    返回是否至少有一种推送方式成功
    """
    # 检查全局推送开关
    if not push_config.get("PUSH_ENABLED"):
        logger.info("消息推送功能已关闭，跳过推送")
        return False
        
    success = False
    
    # 企业微信机器人推送
    if push_config.get("QYWX_KEY"):
        if wecom_bot(content, is_tech_only):
            success = True
    
    # 钉钉机器人推送
    if push_config.get("DD_BOT_TOKEN") and push_config.get("DD_BOT_SECRET"):
        if dingding_bot(content, is_tech_only):
            success = True
    
    # 飞书机器人推送
    if push_config.get("FSKEY"):
        if feishu_bot(content, is_tech_only):
            success = True
    
    # Telegram机器人推送
    if push_config.get("TG_BOT_TOKEN") and push_config.get("TG_USER_ID"):
        if telegram_bot(content, is_tech_only):
            success = True
    
    # Bark推送
    if push_config.get("BARK_PUSH"):
        if bark(content, is_tech_only):
            success = True
    
    # PushPlus推送
    if push_config.get("PUSH_PLUS_TOKEN"):
        if pushplus_bot(content, is_tech_only):
            success = True
    
    # Server酱推送
    if push_config.get("PUSH_KEY"):
        if serverJ(content, is_tech_only):
            success = True
    
    # 企业微信应用推送
    if push_config.get("QYWX_AM"):
        if wecom_app(content, is_tech_only):
            success = True
    
    # 原始Webhook推送（兼容旧版本）
    if push_config.get("WEBHOOK_URL"):
        if send_to_webhook(push_config.get("WEBHOOK_URL"), content, is_tech_only):
            success = True
    
    return success