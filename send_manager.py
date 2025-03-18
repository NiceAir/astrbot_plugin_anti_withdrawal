from typing import AsyncGenerator
from astrbot.api import logger
import json
import os
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from data.plugins.astrbot_plugin_anti_withdrawal.error import command_error_handler


class SendManager:
    def __init__(self, user_manager_file):
        super().__init__()
        self.user_manager_file = user_manager_file
        self.send_targets = {}
        self.load_manager()

    def is_admin(self, event: AstrMessageEvent) -> bool:
        return event.role == "admin"

    def normalize_session_id(self, event: AstrMessageEvent) -> str:
        """标准化会话ID，确保格式一致"""
        try:
            target = event.unified_msg_origin
            return target
        except Exception as e:
            logger.error(f"标准化会话ID时出错: {str(e)}")
            return event.unified_msg_origin  # 返回原始ID作为后备

    def parse_user_id(self, event: AstrMessageEvent) -> str:
        sender_id = event.get_sender_id()
        platform = event.get_platform_name()
        manager_id = platform + "_" + sender_id
        return manager_id

    def load_manager(self):
        if os.path.exists(self.user_manager_file):
            try:
                with open(self.user_manager_file, 'r') as f:
                    self.send_targets = json.load(f)
            except Exception as e:
                logger.error(f"加载撤回发送主体失败: {e}")

    def save_manager(self):
        try:
            with open(self.user_manager_file, 'w') as f:
                json.dump(self.send_targets, f)
        except Exception as e:
            logger.error(f"持久化撤回发送主体失败: {e}")

    def set_send_target(self, event: AstrMessageEvent):
        try:
            user = self.parse_user_id(event)
            session = self.normalize_session_id(event)
            self.send_targets[user] = session
            self.save_manager()
        except Exception as e:
            logger.error(f"set_send_target failed: {e}")

    def cancel_send_target(self, event: AstrMessageEvent):
        user = ""
        try:
            user = self.parse_user_id(event)
            del self.send_targets[user]
            self.save_manager()
        except Exception as e:
            logger.info(f"cancel_send_target failed, user:{user}, err: {e}")
        return

    @command_error_handler
    async def handle_send_target(
            self, event: AstrMessageEvent
    ) -> AsyncGenerator[MessageEventResult, None]:
        if not self.is_admin(event):
            yield event.plain_result("权限不足")
            return
        self.set_send_target(event)
        yield event.plain_result("好的")

    @command_error_handler
    async def handle_cancel_send_target(
            self, event: AstrMessageEvent
    ) -> AsyncGenerator[MessageEventResult, None]:
        if not self.is_admin(event):
            yield event.plain_result("权限不足")
            return
        self.cancel_send_target(event)
        yield event.plain_result("好的, 已取消")
