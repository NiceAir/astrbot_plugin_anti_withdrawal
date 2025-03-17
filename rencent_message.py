from collections import deque
from astrbot.core.platform import AstrBotMessage
import time
import threading
from astrbot.api.event import  AstrMessageEvent

from data.plugins.astrbot_plugin_anti_withdrawal.parse import MessageParser


#https://apifox.com/apidoc/shared-69ba62ca-cb7d-437e-85e4-6f3d3df271b1/doc-4801171#%E6%96%87%E6%9C%AC%E6%B6%88%E6%81%AF
def parse_gewechat_message(msg_type, group_id, sender_id,sender_name, raw_message: AstrBotMessage) ->{}:
    msg = {
        "group_id":group_id,
        "sender_id":sender_id,
        "sender_name": sender_name,
        "msg_id":raw_message.get('MsgId', 0),
        "msg_type":msg_type,
        "content": raw_message.get('Content', ""),
    }
    return msg

class RecentMessageQueue:
    def __init__(self, max_age=300):
        self.queue = deque()
        self.max_age = max_age  # 5分钟（秒）
        self.lock = threading.Lock()
        self.message_parser = MessageParser()

    def add_message(self,  event:AstrMessageEvent):
        """添加新消息"""
        with self.lock:
            # 清理过期消息
            now = time.time()
            while self.queue and self.queue[0]['timestamp'] < now - self.max_age:
                self.queue.popleft()

            # 添加新消息
            self.queue.append(self.message_parser.parse_gewechat_message(event))

    def find_message(self, msg_id):
        """查找被撤回的消息"""
        with self.lock:
            # 逆序查找最新匹配项（微信撤回顺序通常后进先出）
            for msg in reversed(self.queue):
                if msg['msg_id'] == msg_id:
                    return msg
            return None
