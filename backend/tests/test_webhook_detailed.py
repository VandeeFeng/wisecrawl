#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试webhook推送功能的详细脚本
可以测试各种推送方式，并输出详细的日志信息
"""

import os
import logging
import sys
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 导入推送函数
from notification.webhook_sender import notify, send_to_webhook, wecom_bot, dingding_bot, feishu_bot, \
    telegram_bot, bark, pushplus_bot, serverJ, wecom_app, push_config

# 测试内容
TEST_CONTENT = """
# 2025-03-12 10:03 科技热点早报

## ** 01 OpenAI开源首个Agent SDK并推出Responses API **  
- [重磅！OpenAI开源首个Ag...](https://mp.weixin.qq.com/s/HkcuJILUGHrVkUDolZLZ6Q) `🏷️AIGC开放社区`

## ** 02 DeepSeek-R2模型发布消息被官方辟谣 **  
- [（更新：消息不实）mentioned De...](https://www.ithome.com/0/836/942.htm) `🏷️IT之家`
- [DeepSeek R2 发布是假消息](https://weibo.com/1642720480/5143305643361663) `🏷️爱范儿`

## ** 03 安徽完成DeepSeek-R1本地化部署并全省推广 **  
- [安徽：率先在全国省级层面完成 ...](https://www.ithome.com/0/836/878.htm) `🏷️IT之家`

## ** 04 华为余承东宣布首款鸿蒙手机下周发布 **  
- [华为将发布首款鸿蒙手机](https://weibo.com/1642720480/5143306589701460) `🏷️爱范儿`

## ** 05 云计算巨头AI战略分化引行业关注 **  
- [云计算巨头AI战略分化：谁将定...](https://mp.weixin.qq.com/s/_as8zmZ2T6FfT3GSlHyhhA) `🏷️AIGC开放社区`

## ** 06 腾讯确认微信核心功能将上线鸿蒙原生版 **  
- [腾讯员工：微信的绝大部分功能都...](https://www.ithome.com/0/837/072.htm) `🏷️IT之家`

## ** 07 华为通报违规招聘事件多人被开除 **  
- [号称华为内部通报“违规招聘”...](https://www.ithome.com/0/837/035.htm) `🏷️IT之家`
- [8点1氪｜华为通报“违规招聘”...](https://www.36kr.com/p/3202513286701572) `🏷️36氪`
- [华为多名负责人因违规被开除](https://weibo.com/1642720480/5143079360923631) `🏷️爱范儿`

## ** 08 稚晖君发布灵犀X2人形机器人新能力 **  
- [稚晖君的机器人又进化了，会骑自...](https://mp.weixin.qq.com/s/cQMf_cJ0dB0dtpRGWfjIcw) `🏷️差评X.PIN`
- [稚晖君和机器人，离不开自行车](https://mp.weixin.qq.com/s/y6pC73FfoG7Z5pxTcxWaHg) `🏷️极客公园`

## ** 09 苹果iOS19或将采用VisionOS设计语言 **  
- [【 <a class="fee...](https://www.coolapk.com/feed/63284680?shareKey=ZGFhZjEzNjMyNjZiNjdkMGU5ZWE~) `🏷️酷安`

## ** 10 富士康发布首款工业大模型FoxBrain **  
- [富士康推出首个大语言模型](https://weibo.com/1642720480/5143043556508052) `🏷️爱范儿`



[查看全部热点](https://hot.tuber.cc/)
"""


def print_config():
    """打印当前配置的推送渠道"""
    print("\n当前配置的推送渠道:")
    channels = {
        "WEBHOOK_URL": "原始Webhook URL",
        "QYWX_KEY": "企业微信机器人",
        "DD_BOT_TOKEN": "钉钉机器人",
        "FSKEY": "飞书机器人",
        "TG_BOT_TOKEN": "Telegram机器人",
        "BARK_PUSH": "Bark",
        "PUSH_PLUS_TOKEN": "PushPlus",
        "PUSH_KEY": "Server酱",
        "QYWX_AM": "企业微信应用"
    }
    
    for key, name in channels.items():
        if push_config.get(key):
            if key == "DD_BOT_TOKEN" and not push_config.get("DD_BOT_SECRET"):
                print(f"  {name}: 配置不完整 (缺少DD_BOT_SECRET)")
            elif key == "TG_BOT_TOKEN" and not push_config.get("TG_USER_ID"):
                print(f"  {name}: 配置不完整 (缺少TG_USER_ID)")
            else:
                print(f"  {name}: 已配置")
        else:
            print(f"  {name}: 未配置")
    print()


def test_all_channels():
    """测试所有配置的推送渠道"""
    print("\n开始测试所有配置的推送渠道...")
    result = notify(TEST_CONTENT)
    print(f"综合测试结果: {'成功' if result else '失败'}\n")
    return result


def test_specific_channel(channel_name, test_func, *args):
    """测试特定的推送渠道"""
    print(f"\n测试 {channel_name} 推送...")
    try:
        result = test_func(*args)
        print(f"{channel_name} 测试结果: {'成功' if result else '失败'}")
        return result
    except Exception as e:
        print(f"{channel_name} 测试出错: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n===== Webhook推送功能测试 =====")
    
    # 打印当前配置
    print_config()
    
    # 测试所有渠道
    all_result = test_all_channels()
    
    # 如果综合测试失败，尝试单独测试各个渠道
    if not all_result:
        print("\n开始单独测试各个渠道...")
        
        # 测试企业微信机器人
        if push_config.get("QYWX_KEY"):
            test_specific_channel("企业微信机器人", wecom_bot, TEST_CONTENT)
        
        # 测试钉钉机器人
        if push_config.get("DD_BOT_TOKEN") and push_config.get("DD_BOT_SECRET"):
            test_specific_channel("钉钉机器人", dingding_bot, TEST_CONTENT)
        
        # 测试飞书机器人
        if push_config.get("FSKEY"):
            test_specific_channel("飞书机器人", feishu_bot, TEST_CONTENT)
        
        # 测试Telegram机器人
        if push_config.get("TG_BOT_TOKEN") and push_config.get("TG_USER_ID"):
            test_specific_channel("Telegram机器人", telegram_bot, TEST_CONTENT)
        
        # 测试Bark
        if push_config.get("BARK_PUSH"):
            test_specific_channel("Bark", bark, TEST_CONTENT)
        
        # 测试PushPlus
        if push_config.get("PUSH_PLUS_TOKEN"):
            test_specific_channel("PushPlus", pushplus_bot, TEST_CONTENT)
        
        # 测试Server酱
        if push_config.get("PUSH_KEY"):
            test_specific_channel("Server酱", serverJ, TEST_CONTENT)
        
        # 测试企业微信应用
        if push_config.get("QYWX_AM"):
            test_specific_channel("企业微信应用", wecom_app, TEST_CONTENT)
        
        # 测试原始Webhook
        if push_config.get("WEBHOOK_URL"):
            test_specific_channel("原始Webhook", send_to_webhook, 
                                push_config.get("WEBHOOK_URL"), TEST_CONTENT)
    
    print("\n===== 测试完成 =====")
    
    # 检查是否生成了推送内容文件
    import os
    webhook_dir = os.path.join("data", "webhook")
    if os.path.exists(webhook_dir) and os.listdir(webhook_dir):
        print(f"\n已在 {webhook_dir} 目录下生成推送内容文件")
        for file in os.listdir(webhook_dir):
            if file.endswith(".md") or file.endswith(".json"):
                print(f"  - {file}")
    else:
        print("\n未生成任何推送内容文件，所有推送可能都失败了")


if __name__ == '__main__':
    main()