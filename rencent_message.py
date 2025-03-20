import json
from collections import deque
import time
import signal
import atexit
from datetime import datetime
from pathlib import Path
import threading
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from data.plugins.astrbot_plugin_anti_withdrawal.parse import MessageParser


class RecentMessageQueue:
    def __init__(self, persist_file, max_age=240):
        self.queue = deque()
        self.max_age = max_age  # 4分钟（秒）
        self.lock = threading.Lock()
        self.message_parser = MessageParser()
        self.persist_file = Path(persist_file)
        self._load_from_disk()

        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
        atexit.register(self._save_to_disk)

    def add_message(self, tmp_dict, event: AstrMessageEvent):
        """添加新消息"""
        with self.lock:
            # 清理过期消息
            now = time.time()
            self._clean_expired(now)

            # 添加新消息
            self.queue.append(self.message_parser.parse_gewechat_message(tmp_dict, event))

    def _clean_expired(self, now=None):
        """清理过期消息"""
        now = now or time.time()
        while self.queue and self.queue[0]['timestamp'] < now - self.max_age:
            self.queue.popleft()

    def find_message(self, msg_id) -> {}:
        """查找被撤回的消息"""
        with self.lock:
            # 逆序查找最新匹配项（微信撤回顺序通常后进先出）
            for msg in reversed(self.queue):
                if str(msg['msg_id']) == msg_id:
                    self.queue.remove(msg)
                    return msg
            return None

    def _save_to_disk(self, signum=None, frame=None):
        """持久化到磁盘"""
        with self.lock:
            # 保存前再次清理过期数据
            self._clean_expired()

            data = {
                'meta': {
                    'saved_at': datetime.now().isoformat(),
                    'max_age': self.max_age,
                    'count': len(self.queue)
                },
                'data': list(self.queue)
            }

            try:
                with open(self.persist_file, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info(f"防撤回插件 队列已持久化，保存消息数：{len(self.queue)}")
            except Exception as e:
                logger.error(f"防撤回插件 持久化失败：{str(e)}")

    def _load_from_disk(self):
        """从磁盘加载"""
        if not self.persist_file.exists():
            return

        try:
            with open(self.persist_file, 'r') as f:
                data = json.load(f)

            # 校验数据有效性
            if not isinstance(data.get('data'), list):
                raise ValueError("Invalid data format")

            # 转换时间戳并过滤过期数据
            now = time.time()
            valid_messages = [
                msg for msg in data['data']
                if isinstance(msg.get('timestamp'), (int, float)) and
                   msg['timestamp'] > now - self.max_age
            ]

            with self.lock:
                self.queue.extend(valid_messages)
                logger.info(f"防撤回插件已从磁盘加载 {len(valid_messages)} 条有效消息")

        except Exception as e:
            logger.error(f"防撤回插件加载持久化数据失败：{str(e)}")
            # 损坏文件处理

            self.persist_file.rename(f"{self.persist_file}.corrupted")

    def save_to_disk(self):
        self._save_to_disk()

    def _handle_exit(self, signum, frame):
        """信号处理"""
        logger.info(f"\n防撤回插件 接收到终止信号 {signum}, 开始保存...")
        self._save_to_disk()
        exit(0)

    def print_msg_queue(self):
        count = self.queue.__len__()
        print(f"queue.count:{count}")
        for msg in self.queue:
            print(json.dumps(msg, ensure_ascii=False))

        print("-----------------end----------------")
