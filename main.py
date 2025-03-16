import json

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import event_message_type, EventMessageType
from astrbot.core.platform import AstrBotMessage


@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    def custom_serializer(obj):
        if isinstance(obj, AstrBotMessage):
            return {
                "type": str(obj.type),
                "self_id":obj.self_id,
                "session_id":obj.session_id,
                "message_id":obj.message_id,
                "group_id":obj.group_id,
                "sender_id":obj.sender.user_id,
                "sender_name": obj.sender.nickname,
                "message": obj.message,
                "message_str": obj.message_str,
                "raw_message": obj.raw_message,
                "timestamp": obj.timestamp,
            }
        raise TypeError(f"Type {type(obj)} not serializable")
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        '''这是一个 hello world 指令''' # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息


    @event_message_type(EventMessageType.ALL, priority=3)
    async def on_all_message(self, event: AstrMessageEvent):
        msg = json.dumps(event.message_obj, default=self.custom_serializer)
        logger.info(f"on_all_message, sender:{event.get_sender_id()},{msg}")
        yield event.plain_result("收到了一条消息。")




    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''
