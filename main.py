import json
from tokenize import group

from data.plugins.astrbot_plugin_anti_withdrawal.parse import MessageParser
from data.plugins.astrbot_plugin_anti_withdrawal.rencent_message import RecentMessageQueue
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import event_message_type, EventMessageType
from astrbot.core.platform import AstrBotMessage
from collections import deque
from datetime import datetime, timedelta
from astrbot.core.platform.sources.gewechat.gewechat_platform_adapter import GewechatPlatformAdapter,GewechatPlatformEvent



@register("anti_withdrawal", "NiceAir", "一个简单的微信防撤回插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.message_queue = RecentMessageQueue()
        self.message_parser = MessageParser()


    @event_message_type(EventMessageType.ALL, priority=3)
    async def on_all_message(self, event: AstrMessageEvent):
        # 如果是管理者，发的消息，那么不处理。
        if event.get_platform_name() == "gewechat":
            simple_msg = self.message_parser.parse_message_obj(event.message_obj.raw_message)
            if simple_msg['is_withdrawal']:
                withdrawal_info = self.message_queue.find_message(simple_msg['withdrawal_msgid'])
                logger.info(f"withdrawal_info:{json.dumps(withdrawal_info, ensure_ascii=False)}")
                yield event.plain_result("撤回了一条消息。")
            else:
                self.message_queue.add_message(simple_msg, event)
                yield event.plain_result("收到了一条消息。")

        self.message_queue.print_msg_queue()