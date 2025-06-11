import json

from astrbot.api.event import AstrMessageEvent
from astrbot.core.platform import AstrBotMessage
import xml.etree.ElementTree as ET
import time
import logging
import re
from datetime import datetime
from astrbot.api.message_components import *
from astrbot.core.message.components import BaseMessageComponent


def parse_msg_type(msg_type_code) -> str:
    match msg_type_code:
        case 1:
            return "文本"
        case 3:
            return "图片"
        case 34:
            return "语音"
        case 42:
            return "名片"
        case 43:
            return "视频"
        case 47:
            return "emoji表情"
        case 49:
            return "链接或文件或小程序或引用"

        case _:
            return "未知"


class MessageParser(AstrBotMessage):
    def __init__(self):
        super().__init__()

    # https://apifox.com/apidoc/shared-69ba62ca-cb7d-437e-85e4-6f3d3df271b1/doc-4801171#%E6%96%87%E6%9C%AC%E6%B6%88%E6%81%AF
    def parse_gewechat_message(self, tmp_dict, event: AstrMessageEvent) -> {}:
        raw_message = event.message_obj.raw_message
        group_id = event.get_group_id()
        msg_id = tmp_dict.get('msg_id', 0)
        new_msg_id = tmp_dict.get('new_msg_id', 0)
        if group_id != "":
            msg_id = new_msg_id

        msg = {
            "group_id": group_id,
            "sender_id": event.get_sender_id(),
            "sender_name": event.get_sender_name(),
            "msg_id": msg_id,
            "new_msg_id": new_msg_id,
            "msg_type": tmp_dict.get('msg_type', 0),
            "content": tmp_dict.get('content', ""),
            "replacemsg": tmp_dict.get('replacemsg', ""),
            'timestamp': time.time(),
            "message_type": tmp_dict.get('message_type', ""),
            "type_message_str": tmp_dict.get('type_message_str', ""),
        }
        return msg

    def parse_send_message(self, history_msg, withdrawal_info, group_name, group_id) -> {}:
        try:
            dt_object = datetime.fromtimestamp(history_msg['timestamp'])
            readable_time = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")

            if group_name != "":
                content = "在群聊 " + group_name + " 中"
                content = content + "\n" + withdrawal_info['replacemsg'] + "\n发送时间: " + readable_time
            else:
                content = withdrawal_info['replacemsg'] + "\n发送时间: " + readable_time

            if history_msg.get('content', "") != "":
                content = content + "\n" + history_msg['content']

            return {
                "content": content,
                "group_id": group_id,
                "message_type": history_msg.get('message_type', "text"),
                "new_msg_id": history_msg.get('new_msg_id'), # 缓存媒体资源的key
                "type_message_str": history_msg['type_message_str'],

            }
        except Exception as e:
            logging.error(e)
            return {
                "group_id": group_id,
            }

    def parse_message_obj(self, event: AstrMessageEvent, is_private_chat, raw_message: object) -> {}:
        msg = {
            "is_withdrawal": False,
            "content": "",
            "message_type": "text",
            # "img_paths": [],
            # 'voice_paths': [],
            "type_message_str": "",
        }

        try:
            msg_type = raw_message.get('msg_type', 0)

            messages = event.get_messages()
            message = None
            if len(messages) != 0:
                message = messages[0]
            content = raw_message.get("content", "")
            data = content.get('str', "")
            if not is_private_chat and re.match(r'^.*?:\n', data):
                data = data.split(':\n', 1)[-1]

            if msg_type == 10002:
                if re.match(r'^.*?:\n<sysmsg', data):
                    split_index = data.find('<')
                    data = data[split_index:]

                root = ET.fromstring(data)
                if root.attrib.get('type') == 'revokemsg':
                    msg['is_withdrawal'] = True
                    msg['replacemsg'] = root.find('.//replacemsg').text
                    if is_private_chat:
                        msg['withdrawal_msgid'] = root.find('.//msgid').text
                    else:
                        msg['withdrawal_msgid'] = root.find('.//newmsgid').text

            elif msg_type == 1:
                msg['content'] = data
            elif msg_type == 3:
                if isinstance(message, Image):
                    msg['type_message_str'] = json.dumps({"image_path": message.path}, ensure_ascii=False)
                    msg['message_type'] = "image"
            elif msg_type == 43:  # 视频
                if isinstance(message, Video):
                    msg['type_message_str'] = ""
                    msg['message_type'] = "video"
            elif msg_type == 47:
                if isinstance(message, WechatEmoji):  # emoji
                    msg['type_message_str'] = ""
                    msg['message_type'] = "emoji"
            elif msg_type == 49:  # 很多，其中就有引用
                if isinstance(message, Reply):
                    m = vars(message)
                    m.pop("chain")
                    msg['type_message_str'] = ""
                    msg['message_type'] = "reply"

            # todo: astrbot 暂不支持直接使用缓存的语音文件
            # elif msg_type == 34:
            #     for item in event.get_messages():
            #         if isinstance(item, Record):
            #             msg['voice_paths'].append(item.file)
            else:
                msg['content'] = "消息类型:【" + parse_msg_type(msg_type) + "】无法解析"

            msg['msg_id'] = raw_message.get('msg_id', 0)
            msg['new_msg_id'] = raw_message.get('new_msg_id', 0)
            msg['msg_type'] = msg_type
        except Exception as e:
            logging.error(e)

        return msg
