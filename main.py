import json

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import event_message_type, EventMessageType
from astrbot.core.platform import AstrBotMessage
from collections import deque
from datetime import datetime, timedelta


def custom_serializer(obj):
    if isinstance(obj, AstrBotMessage):
        return {
            "type": str(obj.type),
            "self_id": obj.self_id,
            "session_id": obj.session_id,
            "message_id": obj.message_id,
            "group_id": obj.group_id,
            "sender_id": obj.sender.user_id,
            "sender_name": obj.sender.nickname,
            "message": obj.message,
            "message_str": obj.message_str,
            "raw_message": obj.raw_message,
            "timestamp": obj.timestamp,
        }
    raise TypeError(f"Type {type(obj)} not serializable")


@register("anti_withdrawal", "NiceAir", "一个简单的微信防撤回插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.message_queue = deque()

    def record_messages(self, msg):
        try:
            current_time = datetime.now()
            self.message_queue.append((msg, current_time))
            # 清理超过5分钟的消息
            while self.message_queue and current_time - self.message_queue[0][1] > timedelta(minutes=5):
                self.message_queue.popleft()
        except Exception as e:
            logger.error(f"record_messages: {str(e)}")





    # 在哪，谁，时间，发了啥消息
    def parse_wechat_message(self, event: AstrMessageEvent):
        platform = event.get_platform_name()
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()
        group_id = event.get_group_id()
        raw_message = event.message_obj.raw_message
        send_time = event.message_obj.timestamp

        logger.info(f"{platform, sender_id, sender_name, group_id, raw_message, send_time}")


    @event_message_type(EventMessageType.ALL, priority=3)
    async def on_all_message(self, event: AstrMessageEvent):
        self.parse_wechat_message(event)
        logger.info(event.message_obj)
        yield event.plain_result("收到了一条消息。")

    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''
