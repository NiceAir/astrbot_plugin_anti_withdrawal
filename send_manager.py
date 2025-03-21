from typing import AsyncGenerator
from astrbot.api import logger
import json
import os
import traceback
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from data.plugins.astrbot_plugin_anti_withdrawal.error import command_error_handler
from astrbot.core.utils.shared_preferences import SharedPreferences

white_list_flag = "in_white_list:"


class SendManager:
    def __init__(self, context, user_manager_file, path):
        super().__init__()
        self.context = context
        self.user_manager_file = user_manager_file
        self.send_targets = {}
        self.load_manager()
        self.want_to_receive_map = SharedPreferences(path=path)

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

    def set_white_list(self, platform, group_id, uid) -> bool:
        try:
            user = platform + "_" + uid
            if self.send_targets.get(user, "") == "":
                self.send_targets[user] = white_list_flag + group_id
                self.save_manager()
            return True
        except Exception as e:
            logger.error(f"set_send_target failed: {e}")
            return False

    def set_want_to_receive(self, event: AstrMessageEvent) -> bool:
        try:
            user = self.parse_user_id(event)
            session = self.normalize_session_id(event)
            self.want_to_receive_map.put(f"want_to_receive_{user}", session)
            logger.info(f"有人申请要撤回的消息{user}， {session}")
            return True
        except Exception as e:
            logger.info(f"set_want_to_receive failed, err: {e}")
            return False

    def want_to_receive_session(self, user) -> str:
        try:
            return self.want_to_receive_map.get(f"want_to_receive_{user}")
        except Exception as e:
            logger.info(f"set_want_to_receive failed, err: {e}")
            return ""

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

    @command_error_handler
    async def handle_set_white_list(
            self, event: AstrMessageEvent
    ) -> AsyncGenerator[MessageEventResult, None]:
        if not self.is_admin(event):
            yield event.plain_result("权限不足")
            return

        message = event.message_obj.message_str
        info = message.split(' ')
        if len(info) != 3:
            yield event.plain_result("输入参数错误")
            return
        group_id, uid = info[1], info[2]
        if group_id == "" or uid == "":
            yield event.plain_result("输入参数错误")
            return

        if self.set_white_list(event.get_platform_name(), group_id, uid):
            yield event.plain_result("好的, 已设置")
        else:
            yield event.plain_result("服务器出错")

    @command_error_handler
    async def handle_want_to_receive(
            self, event: AstrMessageEvent
    ) -> AsyncGenerator[MessageEventResult, None]:
        if self.set_want_to_receive(event):
            yield event.plain_result("有了就发你哦")
        else:
            yield event.plain_result("失败")

    async def deal_send_withdrawal(self, out_put) -> None:
        try:
            text = out_put.get('content', "")
            # 创建消息段列表
            from astrbot.api.message_components import Plain, Image, Record
            message_segments = [Plain(text)]

            img_paths = out_put.get('img_paths', [])
            for img_path in img_paths:
                message_segments.append(Image(file=img_path, url=img_path))
            voice_paths = out_put.get('voice_paths', [])
            for voice_path in voice_paths:
                message_segments.append(Record(file=voice_path, url=voice_path))

            # 使用send_message发送消息
            from astrbot.api.event import MessageChain
            message_chain = MessageChain(message_segments)

            for user, session in self.send_targets.items():
                try:
                    if session.startswith(white_list_flag):
                        cur_group_id = out_put.get('group_id', "")
                        target_group_id = session[len(white_list_flag):]
                        if cur_group_id != "" and cur_group_id == target_group_id:
                            session = self.want_to_receive_session(user)
                        else:
                            continue

                    await self.context.send_message(session, message_chain)
                    logger.info(f"已向 {session} 发送被撤回的消息")
                except Exception as e:
                    logger.error(f"向 {session} 发送消息失败：{str(e)}")
                    logger.error(traceback.format_exc())
                    return

        except Exception as e:
            logger.error(f"执行任务时出错: {str(e)}")
            logger.error(traceback.format_exc())
