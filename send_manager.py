from typing import AsyncGenerator
from astrbot.api import logger
import traceback
from astrbot.api.event import AstrMessageEvent, MessageEventResult, MessageChain
from data.plugins.astrbot_plugin_anti_withdrawal.error import command_error_handler
from astrbot.core.utils.shared_preferences import SharedPreferences
from astrbot.api.message_components import *
from typing import List

white_list_flag = "in_white_list:"


class SendManager:
    def __init__(self, context, user_manager_file, white_list_file, path):
        super().__init__()
        self.context = context
        self.user_manager_file = user_manager_file
        self.white_list_file = white_list_file
        self.send_targets = {}
        self.white_list = {}
        self.load_manager()
        self.load_manager_v2()
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

    def load_manager_v2(self):
        if os.path.exists(self.white_list_file):
            try:
                with open(self.white_list_file, 'r') as f:
                    self.white_list = json.load(f)
            except Exception as e:
                logger.error(f"加载撤回发送主体失败: {e}")

    def save_manager(self):
        try:
            with open(self.user_manager_file, 'w') as f:
                json.dump(self.send_targets, f)
        except Exception as e:
            logger.error(f"持久化撤回发送主体失败: {e}")

    def save_manager_v2(self):
        try:
            with open(self.white_list_file, 'w') as f:
                json.dump(self.white_list, f)
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
            # 添加白名单，一个用户可以有多个群
            if self.white_list.get(user, None) is None:
                self.white_list[user] = []
            self.white_list[user].append(group_id)
            self.save_manager_v2()

            # if self.send_targets.get(user, "") == "":
            #     self.send_targets[user] = white_list_flag + group_id
            #     self.save_manager()
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

    def make_message_list(self, out_put) -> List[BaseMessageComponent]:
        text = out_put.get('content', "")
        # 创建消息段列表
        message_segments = [Plain(text)]

        message_type = out_put.get('message_type', "")
        type_message_str = out_put.get('type_message_str', "")
        if type_message_str == "":
            return message_segments

        type_massage = json.loads(type_message_str)
        match message_type:
            case "text":
                message_segments.append(Plain(type_message_str))
            case "image":
                file = type_massage.get("file", "")
                url = type_massage.get("url", "")
                message_segments.append(Image(file=file, url=url))
            case "video":
                cover = type_massage.get("cover", "")
                message_segments.append(Video(file="", cover=cover))
            case "emoji":
                md5 = type_massage.get("md5", "")
                md5_len = type_massage.get("md5_len", 0)
                message_segments.append(WechatEmoji(md5=md5, md5_len=md5_len))
            case "reply":
                sender_nickname = type_massage.get("sender_nickname", "")
                message_str = type_massage.get("message_str", "")
                message_segments.append(Plain(f"引用{sender_nickname}的消息，说:{message_str}"))

        return message_segments

    async def deal_send_withdrawal(self, out_put) -> None:
        cur_group_id = out_put.get('group_id', "")
        try:
            message_list = self.make_message_list(out_put)
            message_chain = MessageChain(message_list)

            for user, session in self.send_targets.items():
                try:
                    await self.context.send_message(session, message_chain)
                    logger.info(f"已向 {session} 发送被撤回的消息")
                except Exception as e:
                    logger.error(f"向 {session} 发送消息失败：{str(e)}")
                    logger.error(traceback.format_exc())
                    return
                
            for user, group_ids in self.white_list.items():
                for group_id in group_ids:
                    try:
                        if cur_group_id != "" and cur_group_id == group_id:
                            session = self.want_to_receive_session(user)
                            await self.context.send_message(session, message_chain)
                            logger.info(f"已向 {session} 发送被撤回的消息")
                    except Exception as e:
                        logger.error(f"向 {session} 发送消息失败：{str(e)}")

        except Exception as e:
            logger.error(f"执行任务时出错: {str(e)}")
            logger.error(traceback.format_exc())
