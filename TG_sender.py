from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaWebPage
import asyncio
import logging
import re
from datetime import datetime
import os
import csv

class TG_Sender:
    def __init__(self, api_id, api_hash, session_name, target_bot, price_check_bot, source_channel, logger, csv_path='trading_records.csv'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.target_bot = target_bot
        self.price_check_bot = price_check_bot
        self.source_channel_pairs = source_channel
        self.logger = logger
        self.csv_path = csv_path
        
        # 如果CSV文件不存在，创建并写入表头
        if not os.path.exists(csv_path):
            self._create_csv_file()

    def _create_csv_file(self):
        """创建CSV文件并写入表头"""
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Action', 'Price', 'CA'])
    
    async def _save_to_csv(self, action, price, ca):
        """保存记录到CSV文件"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, action, price, ca])
            self.logger.info(f"Record saved: {timestamp}, {action}, {price}, {ca}")
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {str(e)}")
        
    async def start(self):
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.start()
            self.logger.info("Telegram client started successfully")

            if self.source_channel_pairs:
                source_channel_ids = [str(id_str) for id_str in self.source_channel_pairs.keys()]
            #     @self.client.on(events.NewMessage(chats=source_channel_ids))
            #     async def source_channel_msg_handler(event):
            #         try:
            #             body = event.message.text
            #             channel_id = str(event.message.peer_id.channel_id)
                        
            #             # 判断信号类型
            #             signal_type = "BUY" if channel_id == "@debot_watcher_11_bot" else "SELL"
                        
            #             # 提取CA地址
            #             ca_address = self.extract_contract_address(body)
            #             if not ca_address:
            #                 self.logger.info("No CA address found in message")
            #                 return
                            
            #             # 查询价格
            #             price = await self.check_price(ca_address)
            #             if price:
            #                 # 保存记录到CSV
            #                 await self._save_to_csv(signal_type, price, ca_address)
                            
            #                 # 构建并发送消息
            #                 final_message = f"{signal_type} Signal\nCA: {ca_address}\nPrice: {price}"
            #                 await self.send_message(final_message)
                            
            #         except Exception as e:
            #             self.logger.error(f"Error processing message: {str(e)}")

            @self.client.on(events.NewMessage(chats=source_channel_ids))
            async def source_channel_msg_handler(event):
                try:
                    body = event.message.text
                    
                    # 区分是频道消息还是bot消息
                    if hasattr(event.message.peer_id, 'channel_id'):
                        # 频道消息
                        sender_id = str(event.message.peer_id.channel_id)
                    elif hasattr(event.message.peer_id, 'user_id'):
                        # bot消息
                        sender_id = str(event.message.peer_id.user_id)
                    else:
                        self.logger.error("Unknown message source type")
                        return
                    # print('sender_id', sender_id)
                    # 判断信号类型
                    if int(sender_id) == 7611419879:
                        signal_type = "BUY"
                    else:
                        signal_type = "SELL"
                    
                    # 提取CA地址
                    ca_address = self._extract_contract_address(body)
                    if not ca_address:
                        # print(body)
                        self.logger.info("No CA address found in message")
                        return
                        
                    # 查询价格
                    price = await self.check_price(ca_address)
                    if price:
                        # 保存记录到CSV
                        await self._save_to_csv(signal_type, price, ca_address)
                        
                        # 构建并发送消息
                        final_message = f"{signal_type} Signal\nCA: {ca_address}\nPrice: {price}"
                        await self.send_message(final_message)
                        
                except Exception as e:
                    self.logger.error(f"Error processing message: {str(e)}")

        except Exception as e:
            self.logger.error(f"Failed to start Telegram client: {str(e)}")
            raise

    async def check_price(self, ca_address):
        """查询代币价格"""
        try:
            # 获取价格查询bot实体
            price_bot = await self.client.get_entity(self.price_check_bot)
            
            # 发送查询请求
            await self.client.send_message(price_bot, ca_address)

            # 等待一小段时间让bot回复
            await asyncio.sleep(3)
            
            # 立即获取最新的一条消息
            price_response = await self.client.get_messages(price_bot, limit=1)
            price_response = price_response[0] 
            # print('price_response', price_response)

            if price_response:
                # print('\nSTART to extract price\n')
                price = self.extract_price(price_response)
                # print('price Found: ', price)
                return price
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking price: {str(e)}")
            return None

    def extract_price(self, message):
        """从消息中提取价格"""
        
        message_text = message.message

        # print('/n Message Text /n' )

        # 使用正则表达式查找价格模式：价格 $数字
        price_pattern = r'价格\s*\$([0-9.]+)'
        match = re.search(price_pattern, message_text)
        
        if match:
            price = match.group(1)  # 提取价格数字部分
            return price
        
        return None
    
    async def send_message(self, message):
        """发送消息到目标bot"""
        try:
            bot = await self.client.get_entity(self.target_bot)
            
            try:
                await self.client.send_message(bot, '/start')
                await asyncio.sleep(0.1)
            except Exception as e:
                self.logger.info(f"Start command failed or already started: {e}")
            
            await self.client.send_message(bot, message)
            self.logger.info(f"Message sent to bot {self.target_bot}")

        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            
    def _extract_contract_address(self, message):
        """提取CA地址"""
        # 新的匹配模式：匹配 🔥CA: 后面的地址
        debot_pattern = r'🔥CA:\s`*([A-Za-z0-9]{32,})`'
        # 保留原有的两个模式作为备用
        solana_pattern = r'(?:Contract: |Contract Address: |^)([A-Za-z0-9]{32,})\b'
        suspect_pattern = r'(?:Suspected Token Contract Addresses:[^\n]*\n\s*1\.\s*)([A-Za-z0-9]{32,})'
        
        # 首先尝试 DeBot 格式
        debot_matches = re.findall(debot_pattern, message)
        if debot_matches:
            return debot_matches[0]
        
        # 如果没找到，尝试其他格式
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
        
        return None