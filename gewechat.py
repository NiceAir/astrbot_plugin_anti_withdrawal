import requests

from astrbot.core.config import AstrBotConfig
from astrbot.core.utils.shared_preferences import SharedPreferences
import http.client
import json
import aiohttp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core.platform.sources.gewechat.client import SimpleGewechatClient


class GewechatManager():
    def __init__(self, path):
        super().__init__()
        self.group_map = SharedPreferences(path=path)
        self.gewechat_client = None

    def get_group_name(self, event: AstrMessageEvent):
        key = "group_name_" + event.get_platform_name() + "_" + event.get_group_id()
        group_name=  self.group_map.get(key, "")
        if group_name == "":
            group_name = self.get_group_name_from_gewechat(event, event.get_group_id())
            self.group_map.put(key, group_name)
        return group_name


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


    def get_group_name_from_gewechat(self, event: AstrMessageEvent, group_id) -> str:
        try:
            gewe_client = self.get_gewechat_client(event)
            app_id = gewe_client.appid
            headers = gewe_client.headers
            base_url = gewe_client.base_url + "/group/getChatroomInfo"

            payload = json.dumps({
                "appId": app_id,
                "chatroomId": group_id
            })
            headers['Content-Type'] = 'application/json'

            res = requests.post(base_url , headers=headers, data=payload)
            if res.status_code != requests.codes.ok:
                logger.error(f"get_group_name_from_gewechat failed, {res.status_code}, url:{base_url}")
                return group_id
            
            res_json = res.json()
            return str(res_json.get("data", {}).get("nickName", group_id))

        except Exception as e:
            logger.error(f"get_group_name_from_gewechat failed, {e}")
            return group_id
