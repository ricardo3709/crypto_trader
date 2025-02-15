from TG_sender import TG_Sender
import asyncio
import logging
import re
import json

# Telegram API 配置
API_ID = '25033980'          
API_HASH = 'd271063210a3dabc3313416652870981'      
SESSION_NAME = 'msg_sender_session'

# 频道配置
DOGEE = '@dogeebot_bot'  # 目标bot
MONITOR_CHANNEL = '@doge_monitor'  # 监控频道
PRICE_CHECK_BOT = '@GMGN_sol_bot'  # 价格查询bot
SOURCE_CHANNEL_LIST_PATH = 'tg_channel_monitor_list.json'  
COMMAND_CHANNEL = -1002318483892  

# 加载源频道列表
with open(SOURCE_CHANNEL_LIST_PATH, "r", encoding='utf-8') as f:
    channel_pairs = json.load(f)
    source_channel_pairs = {}
    for k, v in channel_pairs.items():
        try:
            key = int(k)
        except ValueError:
            key = k
        source_channel_pairs[key] = v

async def handle_message(message, logger):
    """
    Send msg to monitor channel
    
    """
    await tg_sender.send_message(MONITOR_CHANNEL, message)

def is_trade_signal(message):
    """判断是否为交易信号"""
    # 在这里添加你的交易信号判断逻辑
    pass

def extract_contract_address(message):
    """提取合约地址"""
    solana_pattern = r'(?:Contract: |Contract Address: |^)([A-Za-z0-9]{32,})\b'
    suspect_pattern = r'(?:Suspected Token Contract Addresses:[^\n]*\n\s*1\.\s*)([A-Za-z0-9]{32,})'
    
    matches = []
    solana_matches = re.findall(solana_pattern, message)
    if solana_matches:
        matches.extend(solana_matches)
        
    suspect_matches = re.findall(suspect_pattern, message)
    if suspect_matches:
        matches.extend(suspect_matches)
    
    matches = list(set(matches))
    if len(matches) > 0:
        return matches[0]

async def main():

    _clear_log_file()
    # 设置日志
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        filename='tg_monitor.log'
    )

    main_logger = logging.getLogger(__name__)

    # 创建 TG Sender
    global tg_sender 
    tg_sender = TG_Sender(
        api_id = API_ID,
        api_hash = API_HASH,
        session_name = SESSION_NAME,
        target_bot = MONITOR_CHANNEL,
        price_check_bot = PRICE_CHECK_BOT,
        source_channel = source_channel_pairs,
        logger = main_logger,
        csv_path = 'trading_records.csv',

    )
    
    try:
        # 启动 TG sender
        await tg_sender.start()
        await tg_sender.client.run_until_disconnected()
            
    except KeyboardInterrupt:
        print("Services stopped")
    finally:
        if tg_sender.client:
            await tg_sender.client.disconnect()

def _clear_log_file(log_file='tg_monitor.log'):
    with open(log_file, 'w') as f:
        f.write(f"=== Service Started ===\n")

if __name__ == "__main__":
    asyncio.run(main())