
from astrbot.api.event import  AstrMessageEvent
from astrbot.core.platform import AstrBotMessage
import xml.etree.ElementTree as ET

class MessageParser(AstrBotMessage):
    def __init__(self):
        super().__init__()

    # https://apifox.com/apidoc/shared-69ba62ca-cb7d-437e-85e4-6f3d3df271b1/doc-4801171#%E6%96%87%E6%9C%AC%E6%B6%88%E6%81%AF
    def parse_gewechat_message(self,  event: AstrMessageEvent) -> {}:
        raw_message = event.message_obj.raw_message
        msg = {
            "group_id": event.get_group_id(),
            "sender_id": event.get_sender_id(),
            "sender_name": event.get_sender_name(),
            "msg_id": raw_message.get('MsgId', 0),
            "msg_type": raw_message.get('MsgType', 1),
            "content": raw_message.get('Content', ""),
        }
        return msg


    def parse_message_obj(self, raw_message: object) -> {}:
        msg = {
            "is_withdrawal": False,
        }

        msg_type = raw_message.get('MsgType', 1),
        content = raw_message.get("Content", "")
        data = content.get('string', "")
        if msg_type == 10002:
            root = ET.fromstring(data)
            if root.attrib.get('type') == 'revokemsg':
                msg['is_withdrawal'] = True

        return msg