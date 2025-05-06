# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import asyncio
import queue
import threading
import time
from typing import Callable, Dict, Any


class AsyncAPI:
    """
    异步API接口，模拟异步调用
    """

    def __init__(self):
        self._callbacks: Dict[str, Callable] = {}

    def register_callback(self, request_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        注册回调函数
        :param request_id: 请求ID
        :param callback: 回调函数
        """
        self._callbacks[request_id] = callback

    def unregister_callback(self, request_id: str) -> None:
        """
        注销回调函数
        :param request_id: 请求ID
        """
        if request_id in self._callbacks:
            del self._callbacks[request_id]

    async def request(self, request_id: str, data: Dict[str, Any]) -> None:
        """
        发送异步请求
        :param request_id: 请求ID
        :param data: 请求数据
        """
        print(f"异步请求开始: {request_id}, 数据: {data}")

        # 模拟异步处理
        await asyncio.sleep(2)

        # 模拟请求处理结果
        result = {
            "request_id": request_id,
            "result": f"处理结果-{data.get('value', 'unknown')}",
            "timestamp": time.time()
        }

        # 触发回调
        if request_id in self._callbacks:
            self._callbacks[request_id](result)


class SPI:
    """
    SPI回调接口，用于接收异步请求的结果
    """

    def __init__(self):
        pass

    def on_response(self, result: Dict[str, Any]) -> None:
        """
        回调方法，处理响应结果
        :param result: 响应结果
        """
        print(f"收到回调响应: {result}")


class SyncAPIWrapper:
    """
    同步API封装，将异步API封装为同步调用方式
    """

    def __init__(self, async_api: AsyncAPI, spi: SPI):
        self.async_api = async_api
        self.spi = spi
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
        self.response_queues: Dict[str, queue.Queue] = {}

    def _run_event_loop(self) -> None:
        """
        在独立线程中运行事件循环
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def request(self, request_id: str, data: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
        """
        同步请求方法
        :param request_id: 请求ID
        :param data: 请求数据
        :param timeout: 超时时间(秒)
        :return: 响应结果
        """
        # 创建结果队列
        result_queue = queue.Queue()
        self.response_queues[request_id] = result_queue

        # 定义回调函数
        def callback(result: Dict[str, Any]) -> None:
            self.spi.on_response(result)
            result_queue.put(result)

        # 注册回调
        self.async_api.register_callback(request_id, callback)

        # 提交异步任务
        asyncio.run_coroutine_threadsafe(
            self.async_api.request(request_id, data),
            self.loop
        )

        try:
            # 等待响应结果
            result = result_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            raise TimeoutError(f"请求超时: {request_id}")
        finally:
            # 清理资源
            self.async_api.unregister_callback(request_id)
            del self.response_queues[request_id]

    def close(self) -> None:
        """
        关闭同步封装器
        """
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=1.0)


# 示例使用
def main():
    # 创建异步API实例
    async_api = AsyncAPI()
    spi = SPI()

    # 创建同步封装
    sync_wrapper = SyncAPIWrapper(async_api=async_api, spi=spi)

    try:
        # 同步方式调用异步API
        print("开始同步调用...")
        result1 = sync_wrapper.request("req-001", {"value": "测试1"})
        print(f"同步调用结果1: {result1}")

        result2 = sync_wrapper.request("req-002", {"value": "测试2"})
        print(f"同步调用结果2: {result2}")

        result3 = sync_wrapper.request("req-003", {"value": "测试3"})
        print(f"同步调用结果3: {result3}")

    except Exception as e:
        print(f"调用异常: {e}")
    finally:
        # 关闭同步封装
        sync_wrapper.close()


if __name__ == '__main__':
    main()
