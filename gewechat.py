from astrbot.core.config import AstrBotConfig
from astrbot.core.utils.shared_preferences import SharedPreferences
import http.client
import json
import aiohttp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core.platform.sources.gewechat.client import SimpleGewechatClient


class GewechatManager():
    def __init__(self):
        super().__init__()
        self.group_map = SharedPreferences()
        self.gewechat_client = None

    def get_gewechat_client(self, event: AstrMessageEvent) -> SimpleGewechatClient:
        try:
            if self.gewechat_client is not None:
                return self.gewechat_client

            from astrbot.core.platform.sources.gewechat.gewechat_event import GewechatPlatformEvent
            assert isinstance(event, GewechatPlatformEvent)
            self.gewechat_client = event.client
            return self.gewechat_client
        except Exception as e:
            logger.error(f"get_gewechat_client failed, {e}")

    def load_group_name(self, platform, group_id) -> str:
        try:
            return self.group_map.get(platform + "_" + group_id, group_id)
        except Exception as e:
            logger.error(f"load_group_name failed, {e}")

    def save_group_name(self, platform, group_id, group_name):
        try:
            self.group_map.put(platform + "_" + group_id, group_name)
        except Exception as e:
            logger.error(f"save_group_name failed, {e}")

    def get_group_name_from_gewechat(self, event: AstrMessageEvent, group_id):
        try:
            gewe_client = self.get_gewechat_client(event)
            payload = json.dumps({
                "appId": gewe_client.appid,
                "chatroomId": group_id
            })

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        f"{gewe_client.base_url}/group/getChatroomInfo",
                        headers=gewe_client.headers,
                        json=payload,
                ) as resp:
                    json_blob = await resp.json()

            print(json_blob.decode("utf-8"))
        except Exception as e:
            logger.error(f"get_group_name_from_gewechat failed, {e}")
