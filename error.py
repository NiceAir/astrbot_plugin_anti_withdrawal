from functools import wraps
import traceback
from typing import AsyncGenerator
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api import logger


def command_error_handler(func):
    """命令错误处理装饰器"""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> AsyncGenerator[MessageEventResult, None]:
        try:
            async for result in func(*args, **kwargs):
                yield result
        except ValueError as e:
            # 参数验证错误
            event = args[1] if len(args) > 1 else None
            if event and isinstance(event, AstrMessageEvent):
                yield event.plain_result(f"参数错误: {str(e)}")
        except Exception as e:
            # 其他未预期的错误
            logger.error(f"{func.__name__} 执行出错: {str(e)}")
            logger.error(traceback.format_exc())
            event = args[1] if len(args) > 1 else None
            if event and isinstance(event, AstrMessageEvent):
                yield event.plain_result("操作执行失败，请查看日志获取详细信息")

    return wrapper
