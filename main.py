# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import asyncio
import concurrent.futures
import queue
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Callable, Dict, Any, List, Optional


def format_time_utc8(timestamp: Optional[float] = None) -> str:
    """
    将时间戳转换为UTC+8时区的人类可读格式
    :param timestamp: 时间戳，如果为None则使用当前时间
    :return: 格式化的时间字符串 (YYYY-MM-DD HH:MM:SS)
    """
    if timestamp is None:
        timestamp = time.time()
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    dt_utc8 = dt + timedelta(hours=8)
    return dt_utc8.strftime("%Y-%m-%d %H:%M:%S")


class CallbackResult:
    """
    回调结果类，用于存储回调的结果
    """
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"

    def __init__(self, callback_id: str, status: str = SUCCESS, data: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None):
        self.callback_id = callback_id
        self.status = status
        self.data = data or {}
        self.error = error
        self.timestamp = time.time()
        self.formatted_time = format_time_utc8(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        """
        将结果转换为字典
        :return: 字典形式的结果
        """
        return {
            "callback_id": self.callback_id,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
            "formatted_time": self.formatted_time
        }

    @classmethod
    def create_success(cls, callback_id: str, data: Dict[str, Any]) -> 'CallbackResult':
        """
        创建成功的回调结果
        :param callback_id: 回调ID
        :param data: 回调数据
        :return: 回调结果对象
        """
        return cls(callback_id, cls.SUCCESS, data)

    @classmethod
    def create_failure(cls, callback_id: str, error: str, data: Optional[Dict[str, Any]] = None) -> 'CallbackResult':
        """
        创建失败的回调结果
        :param callback_id: 回调ID
        :param error: 错误信息
        :param data: 附加数据
        :return: 回调结果对象
        """
        return cls(callback_id, cls.FAILURE, data, error)

    @classmethod
    def create_timeout(cls, callback_id: str) -> 'CallbackResult':
        """
        创建超时的回调结果
        :param callback_id: 回调ID
        :return: 回调结果对象
        """
        return cls(callback_id, cls.TIMEOUT, error="回调超时")


class AsyncAPI:
    """
    异步API接口，模拟异步调用
    """

    def __init__(self):
        self._callbacks: Dict[str, Dict[str, Callable]] = {}

    def register_callback(self, request_id: str, callback_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        注册回调函数
        :param request_id: 请求ID
        :param callback_id: 回调ID
        :param callback: 回调函数
        """
        if request_id not in self._callbacks:
            self._callbacks[request_id] = {}
        self._callbacks[request_id][callback_id] = callback

    def unregister_callback(self, request_id: str, callback_id: Optional[str] = None) -> None:
        """
        注销回调函数
        :param request_id: 请求ID
        :param callback_id: 回调ID，如果为None则注销所有该请求的回调
        """
        if request_id in self._callbacks:
            if callback_id is None:
                del self._callbacks[request_id]
            elif callback_id in self._callbacks[request_id]:
                del self._callbacks[request_id][callback_id]
                if not self._callbacks[request_id]:
                    del self._callbacks[request_id]

    async def request(self, request_id: str, data: Dict[str, Any]) -> None:
        """
        发送异步请求
        :param request_id: 请求ID
        :param data: 请求数据
        """
        print(f"异步请求开始: {request_id}, 数据: {data}")

        # 检查是否有对应的回调
        if request_id not in self._callbacks or not self._callbacks[request_id]:
            print(f"警告: 请求 {request_id} 没有注册回调函数")
            return

        # 模拟处理多个回调
        callbacks = list(self._callbacks[request_id].items())
        for index, (callback_id, callback) in enumerate(callbacks):
            # 使用确定性方法决定延迟和成功/失败
            # 对于req-001请求，所有回调都会成功，延迟递增
            # 对于req-002请求，在短时间内只有第一个回调会成功，其余会因为超时失败
            if request_id.startswith("req-001"):
                # 对req-001，使用固定的延迟模式
                delay = 1 + index  # 1, 2, 3, 4秒
                # 固定的成功/失败模式: 1和4失败，2和3成功
                should_fail = (index == 0 or index == 3)

                # 确保第4个回调的延迟不超过超时时间 (10秒)
                if index == 3:  # 第4个回调
                    delay = min(delay, 8)  # 确保不超过10秒超时
            elif request_id.startswith("req-002"):
                # 对req-002，设置较长延迟使大部分回调超时
                delay = 1 if index == 0 else 3  # 第一个回调1秒，其余3秒
                # 只有第一个成功，其他由于超时会失败
                should_fail = False
            elif request_id.startswith("test"):
                # 测试用例使用短延迟
                delay = 0.1
                # 根据测试需求设置失败模式
                should_fail = False
            else:
                # 其他请求使用随机模式
                delay = 1 + (ord(callback_id[-1]) % 3)
                should_fail = (ord(callback_id[-1]) % 5 == 0)

            # 等待指定的延迟时间
            await asyncio.sleep(delay)

            # 根据应否失败标志创建结果
            if should_fail:
                error_msg = f"处理回调 {callback_id} 时发生错误"
                result = CallbackResult.create_failure(
                    callback_id,
                    error_msg,
                    {"request_id": request_id, "partial_data": f"部分数据-{data.get('value', 'unknown')}"}
                ).to_dict()
            else:
                result = CallbackResult.create_success(
                    callback_id,
                    {
                        "request_id": request_id,
                        "result": f"处理结果-{data.get('value', 'unknown')}-{callback_id}",
                    }
                ).to_dict()

            # 触发回调
            try:
                callback(result)
            except Exception as e:
                print(f"触发回调 {callback_id} 时发生异常: {e}")


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
        status = result.get("status", "unknown")
        callback_id = result.get("callback_id", "unknown")
        formatted_time = result.get("formatted_time", format_time_utc8())

        if status == CallbackResult.SUCCESS:
            data = result.get("data", {})
            request_id = data.get("request_id", "unknown")
            result_text = data.get("result", "无结果")
            print(
                f"收到成功回调: [时间: {formatted_time}] 请求ID={request_id}, 回调ID={callback_id}, 结果={result_text}")
        elif status == CallbackResult.FAILURE:
            error = result.get("error", "未知错误")
            data = result.get("data", {})
            request_id = data.get("request_id", "unknown")
            print(f"收到失败回调: [时间: {formatted_time}] 请求ID={request_id}, 回调ID={callback_id}, 错误={error}")
        elif status == CallbackResult.TIMEOUT:
            print(f"回调超时: [时间: {formatted_time}] 回调ID={callback_id}")
        else:
            print(f"收到未知回调: [时间: {formatted_time}] 数据={result}")


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

    def request(self, request_id: str, data: Dict[str, Any],
                callback_count: int = 4, timeout: float = 5.0) -> List[Dict[str, Any]]:
        """
        同步请求方法，等待多个回调结果
        :param request_id: 请求ID
        :param data: 请求数据
        :param callback_count: 回调数量
        :param timeout: 超时时间(秒)
        :return: 所有回调结果的列表
        """
        # 创建结果队列
        result_queue = queue.Queue()
        self.response_queues[request_id] = result_queue

        # 存储所有回调结果
        results: List[Dict[str, Any]] = []

        # 创建回调计数器
        callback_counter = {"count": 0}

        # 预期的回调ID列表
        callback_ids = [f"{request_id}-cb-{i + 1}" for i in range(callback_count)]

        # 定义回调函数
        def callback(result: Dict[str, Any]) -> None:
            self.spi.on_response(result)
            result_queue.put(result)
            callback_counter["count"] += 1

        # 注册所有回调
        for callback_id in callback_ids:
            self.async_api.register_callback(request_id, callback_id, callback)

        # 提交异步任务
        asyncio.run_coroutine_threadsafe(
            self.async_api.request(request_id, data),
            self.loop
        )

        try:
            # 等待所有回调结果或超时
            deadline = time.time() + timeout
            while callback_counter["count"] < callback_count and time.time() < deadline:
                try:
                    # 设置剩余超时时间
                    remaining_timeout = max(0.1, deadline - time.time())
                    result = result_queue.get(timeout=remaining_timeout)
                    results.append(result)
                except queue.Empty:
                    # 队列为空，但可能还有未完成的回调
                    continue

            # 处理未返回的回调（超时）
            received_callback_ids = {result.get("callback_id") for result in results}
            for callback_id in callback_ids:
                if callback_id not in received_callback_ids:
                    timeout_result = CallbackResult.create_timeout(callback_id).to_dict()
                    self.spi.on_response(timeout_result)
                    results.append(timeout_result)

            # 等待一小段时间，确保所有未完成的回调都能够完成，虽然已经超时
            # 这样可以避免任务被取消的警告，同时保持结果的准确性（仍然标记为超时）
            if callback_counter["count"] < callback_count:
                time.sleep(0.2)

            return results

        finally:
            # 清理资源
            for callback_id in callback_ids:
                self.async_api.unregister_callback(request_id, callback_id)
            del self.response_queues[request_id]

    def close(self) -> None:
        """
        关闭同步封装器
        """
        # 取消事件循环中所有待处理的任务
        pending_tasks = set()
        try:
            # 获取事件循环中的所有任务
            pending_tasks = asyncio.all_tasks(self.loop)
        except RuntimeError:
            # 忽略可能的循环未运行错误
            pass

        if pending_tasks:
            # 在事件循环中执行任务取消
            async def cancel_all_tasks():
                # 取消所有任务
                for task in pending_tasks:
                    if not task.done() and not task.cancelled():
                        task.cancel()
                # 等待所有任务取消完成
                await asyncio.gather(*pending_tasks, return_exceptions=True)

            # 在事件循环中安排取消任务
            future = asyncio.run_coroutine_threadsafe(cancel_all_tasks(), self.loop)
            try:
                # 最多等待1秒钟
                future.result(timeout=1.0)
            except (asyncio.CancelledError, concurrent.futures.TimeoutError):
                # 忽略取消和超时错误
                pass

        # 停止事件循环
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)

        # 等待线程结束
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)

        # 关闭事件循环
        try:
            if not self.loop.is_closed():
                self.loop.close()
        except:
            # 忽略关闭错误
            pass


# 示例使用
def main():
    # 创建异步API实例
    async_api = AsyncAPI()
    spi = SPI()

    # 创建同步封装
    sync_wrapper = SyncAPIWrapper(async_api=async_api, spi=spi)

    try:
        # 同步方式调用异步API
        print("\n=== 开始同步调用 (4个回调) ===")
        # 使用一个较长超时，确保所有回调都能完成
        results1 = sync_wrapper.request("req-001", {"value": "测试1"}, callback_count=4, timeout=10.0)
        print(f"\n同步调用结果汇总: 请求ID=req-001, 共{len(results1)}个回调结果")
        success_count = sum(1 for r in results1 if r.get("status") == CallbackResult.SUCCESS)
        failure_count = sum(1 for r in results1 if r.get("status") == CallbackResult.FAILURE)
        timeout_count = sum(1 for r in results1 if r.get("status") == CallbackResult.TIMEOUT)
        print(f"成功: {success_count}, 失败: {failure_count}, 超时: {timeout_count}")

        print("\n=== 开始同步调用 (带超时) ===")
        # 使用2秒的超时，确保req-002请求的2-4号回调会超时
        results2 = sync_wrapper.request("req-002", {"value": "测试2"}, callback_count=4, timeout=2.0)
        print(f"\n同步调用结果汇总: 请求ID=req-002, 共{len(results2)}个回调结果")
        success_count = sum(1 for r in results2 if r.get("status") == CallbackResult.SUCCESS)
        failure_count = sum(1 for r in results2 if r.get("status") == CallbackResult.FAILURE)
        timeout_count = sum(1 for r in results2 if r.get("status") == CallbackResult.TIMEOUT)
        print(f"成功: {success_count}, 失败: {failure_count}, 超时: {timeout_count}")

    except Exception as e:
        print(f"调用异常: {e}")
    finally:
        # 关闭同步封装
        sync_wrapper.close()


if __name__ == '__main__':
    main()
