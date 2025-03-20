import json
from data.plugins.astrbot_plugin_anti_withdrawal.gewechat import GewechatManager
from data.plugins.astrbot_plugin_anti_withdrawal.send_manager import SendManager
from data.plugins.astrbot_plugin_anti_withdrawal.parse import MessageParser
from data.plugins.astrbot_plugin_anti_withdrawal.rencent_message import RecentMessageQueue
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.config import AstrBotConfig
from astrbot.api import logger
from astrbot.api.all import event_message_type, EventMessageType
import os
from astrbot.api.event.filter import permission_type, PermissionType


def get_nickname(conf: AstrBotConfig) -> str:
    platforms = conf.get('platform', [])
    for p in platforms:
        type = p.get('type', "")
        if type == "gewechat":
            nickname = p.get('nickname', "")
            return nickname

    return ""


def with_project_path(file: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file)


@register("anti_withdrawal", "NiceAir", "一个简单的微信防撤回插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

        try:
            self.gewechat_manager = GewechatManager(with_project_path("gewechat_group_map.json"))
            self.message_queue = RecentMessageQueue(with_project_path("persist_file.json"))
            self.message_parser = MessageParser()
            self.manager = SendManager(context, with_project_path("user_manager_file.json"),
                                       with_project_path("want_to_receive_map.json"))
        except Exception as e:
            logger.error(f"防撤回插件加载失败, {e}")

    @event_message_type(EventMessageType.ALL, priority=3)
    async def on_all_message(self, event: AstrMessageEvent):
        # 如果是管理者发的消息，那么不记录不处理
        if event.is_admin():
            return
        try:
            if event.get_platform_name() == "gewechat":
                simple_msg = self.message_parser.parse_message_obj(event.is_private_chat(),
                                                                   event.message_obj.raw_message)
                if simple_msg['is_withdrawal']:
                    group_name = self.gewechat_manager.get_group_name(event)
                    history_msg = self.message_queue.find_message(simple_msg['withdrawal_msgid'])
                    out_put = self.message_parser.parse_send_message(history_msg, simple_msg, group_name,
                                                                     event.get_group_id())
                    await self.manager.deal_send_withdrawal(out_put)
                    logger.info(f"withdrawal_info:{json.dumps(history_msg, ensure_ascii=False)}")
                else:
                    self.message_queue.add_message(simple_msg, event)
                    self.message_queue.print_msg_queue()
        except Exception as e:
            logger.error(e)

    @event_message_type(EventMessageType.PRIVATE_MESSAGE)
    @permission_type(PermissionType.ADMIN)
    @filter.command("把撤回的消息发给我")
    async def set_send_target(self, event: AstrMessageEvent):
        """ 设置把撤回消息发送给谁，只有管理者有权限设置 """
        async for result in self.manager.handle_send_target(event):
            yield result

    @permission_type(PermissionType.ADMIN)
    @event_message_type(EventMessageType.PRIVATE_MESSAGE)
    @filter.command("别给我了")
    async def cancel_send_target(self, event: AstrMessageEvent):
        """ 取消把撤回消息发送的目标，只有管理者有权限设置 """
        async for result in self.manager.handle_cancel_send_target(event):
            yield result

    @permission_type(PermissionType.ADMIN)
    @event_message_type(EventMessageType.PRIVATE_MESSAGE)
    @filter.command("设置白名单")
    async def set_white_list(self, event: AstrMessageEvent):
        """ 设置让群里的某个人接收该群的撤回消息，只有管理者有权限设置 """
        async for result in self.manager.handle_set_white_list(event):
            yield result

    @event_message_type(EventMessageType.PRIVATE_MESSAGE)
    @filter.command("我要撤回的消息")
    async def want_to_receive(self, event: AstrMessageEvent):
        """ 设置让群里的某个人接收该群的撤回消息，只有管理者有权限设置 """
        async for result in self.manager.handle_want_to_receive(event):
            yield result
