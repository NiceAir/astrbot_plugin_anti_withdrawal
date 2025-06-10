import requests

from astrbot.core.config import AstrBotConfig
from astrbot.core.utils.shared_preferences import SharedPreferences
import http.client
import json
import aiohttp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core.platform.sources.wechatpadpro.wechatpadpro_adapter import WeChatPadProAdapter


class WechatpadproManager():
    def __init__(self, path):
        super().__init__()
        self.group_map = SharedPreferences(path=path)
        self.adapter = None

    async def get_group_name(self, event: AstrMessageEvent) -> str:
        group_id = event.get_group_id()
        if group_id == "":
            return ""
        key = "group_name_" + event.get_platform_name() + "_" + group_id
        group_name = self.group_map.get(key, "")
        if group_name == "":
            group_name = await self.get_group_name_from_adapter(event, event.get_group_id())
            self.group_map.put(key, group_name)
        return group_name

    async def get_group_name_from_adapter(self, event: AstrMessageEvent, group_id) -> str:
        adapter = self.get_adapter_client(event)
        url = f"{adapter.base_url}/group/GetChatRoomInfo"
        params = {"key": adapter.auth_key}
        payload = {"ChatRoomWxIdList": [group_id]}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, params=params, json=payload) as response:
                    response_data = await response.json()
                    # 修正成功判断条件和数据提取路径
                    if response.status == 200 and response_data.get("Code") == 200:
                        data = response_data.get("Data")
                        contactList = data.get('contactList')
                        if contactList:
                            name = contactList[0]['nickName']['str']
                            return name
                    else:
                        logger.error(
                            f"获取群详情失败: {response.status}, {response_data}"
                        )
                        return None
            except aiohttp.ClientConnectorError as e:
                logger.error(f"连接到 WeChatPadPro 服务失败: {e}")
                return None
            except Exception as e:
                logger.error(f"获取群详情时发生错误: {e}")
                return None

    def get_adapter_client(self, event: AstrMessageEvent) -> WeChatPadProAdapter:
        try:
            if self.adapter is not None:
                return self.adapter

            from astrbot.core.platform.sources.wechatpadpro.wechatpadpro_message_event import WeChatPadProMessageEvent
            assert isinstance(event, WeChatPadProMessageEvent)
            self.adapter = event.adapter
            return self.adapter
        except Exception as e:
            logger.error(f"get_wechatpadpro_adapter failed, {e}")
