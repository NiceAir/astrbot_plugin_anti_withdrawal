from astrbot.api.event import AstrMessageEvent
from astrbot.core.platform import AstrBotMessage
import xml.etree.ElementTree as ET
import time
import logging
import re
from datetime import datetime


class MessageParser(AstrBotMessage):
    def __init__(self):
        super().__init__()

    # https://apifox.com/apidoc/shared-69ba62ca-cb7d-437e-85e4-6f3d3df271b1/doc-4801171#%E6%96%87%E6%9C%AC%E6%B6%88%E6%81%AF
    def parse_gewechat_message(self, tmp_dict, event: AstrMessageEvent) -> {}:
        raw_message = event.message_obj.raw_message
        group_id = event.get_group_id()
        msg_id = raw_message.get('MsgId', 0)
        if group_id != "":
            msg_id = raw_message.get('NewMsgId', 0)

        msg = {
            "group_id": group_id,
            "sender_id": event.get_sender_id(),
            "sender_name": event.get_sender_name(),
            "msg_id": msg_id,
            "msg_type": raw_message.get('MsgType', 0),
            "content": tmp_dict.get('content', 0),
            "replacemsg": tmp_dict.get('replacemsg', ""),
            'timestamp': time.time(),
        }
        return msg

    def parse_send_message(self, history_msg, withdrawal_info) -> {}:
        try:
            content = ""
            group_id = history_msg['group_id']
            if group_id != "":
                content = "在群聊" + group_id + "中"

            dt_object = datetime.fromtimestamp(history_msg['timestamp'])
            readable_time = dt_object.strftime("%Y-%m-%d %H:%M:%S.%f")

            content = content + "\n" + withdrawal_info['replacemsg'] + "\n发送时间: " + readable_time

            if history_msg['msg_type'] == 1:
                content = content + "\n" + history_msg['content']
            return {
                "content": content
            }
        except Exception as e:
            logging.error(e)
            return {}

    def parse_message_obj(self, is_private_chat, raw_message: object) -> {}:
        msg = {
            "is_withdrawal": False,
        }

        try:
            msg_type = raw_message.get('MsgType', 0)

            content = raw_message.get("Content", "")
            data = content.get('string', "")
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
            else:
                msg['content'] = "消息类型:" + str(msg_type) + "无法解析"

            msg['msg_type'] = msg_type
        except Exception as e:
            logging.error(e)

        return msg
