import asyncio
import time
import unittest
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from main import AsyncAPI, SPI, SyncAPIWrapper


class TestSyncAPIWrapper(unittest.TestCase):
    """
    测试同步API封装器
    """

    def setUp(self) -> None:
        """
        测试前准备
        """
        self.async_api = AsyncAPI()
        self.spi = SPI()
        self.sync_wrapper = SyncAPIWrapper(self.async_api, self.spi)

    def tearDown(self) -> None:
        """
        测试后清理
        """
        self.sync_wrapper.close()

    def test_request_success(self) -> None:
        """
        测试正常请求成功的情况
        执行命令:
        python -m unittest tests.test_sync_wrapper.TestSyncAPIWrapper.test_request_success
        """
        # 模拟异步请求方法
        original_request = self.async_api.request

        async def mock_request(request_id: str, data: Dict[str, Any]) -> None:
            # 直接触发回调，不等待
            timestamp = time.time()
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            dt_utc8 = dt + timedelta(hours=8)
            formatted_time = dt_utc8.strftime("%Y-%m-%d %H:%M:%S")
            
            result = {
                "request_id": request_id,
                "result": f"测试结果-{data.get('value', 'unknown')}",
                "timestamp": timestamp,
                "formatted_time": formatted_time
            }
            if request_id in self.async_api._callbacks:
                self.async_api._callbacks[request_id](result)

        # 替换异步请求方法
        self.async_api.request = mock_request

        try:
            # 执行同步请求
            result = self.sync_wrapper.request("test-001", {"value": "测试数据"})

            # 验证结果
            self.assertEqual(result["request_id"], "test-001")
            self.assertEqual(result["result"], "测试结果-测试数据")
            self.assertIn("timestamp", result)
            self.assertIn("formatted_time", result)
            self.assertIsInstance(result["formatted_time"], str)
        finally:
            # 恢复原始方法
            self.async_api.request = original_request

    def test_request_timeout(self) -> None:
        """
        测试请求超时的情况
        执行命令:
        python -m unittest tests.test_sync_wrapper.TestSyncAPIWrapper.test_request_timeout
        """
        # 模拟异步请求方法
        original_request = self.async_api.request

        async def mock_request_timeout(request_id: str, data: Dict[str, Any]) -> None:
            # 不触发回调，模拟超时
            pass

        # 替换异步请求方法
        self.async_api.request = mock_request_timeout

        try:
            # 执行同步请求，设置较短的超时时间
            with self.assertRaises(TimeoutError):
                self.sync_wrapper.request("test-002", {"value": "测试数据"}, timeout=0.1)
        finally:
            # 恢复原始方法
            self.async_api.request = original_request

    def test_multiple_requests(self) -> None:
        """
        测试多个请求并发的情况
        执行命令:
        python -m unittest tests.test_sync_wrapper.TestSyncAPIWrapper.test_multiple_requests
        """
        # 模拟异步请求方法
        original_request = self.async_api.request

        request_times = {}

        async def mock_multiple_requests(request_id: str, data: Dict[str, Any]) -> None:
            # 记录请求时间
            timestamp = time.time()
            request_times[request_id] = timestamp
            
            # 不同请求不同延迟
            delay = 0.1 if request_id == "req-1" else 0.2
            await asyncio.sleep(delay)
            
            # 获取当前UTC时间并转换为UTC+8
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            dt_utc8 = dt + timedelta(hours=8)
            formatted_time = dt_utc8.strftime("%Y-%m-%d %H:%M:%S")
            
            # 触发回调
            result = {
                "request_id": request_id,
                "result": f"结果-{data.get('value', 'unknown')}",
                "timestamp": timestamp,
                "formatted_time": formatted_time
            }
            if request_id in self.async_api._callbacks:
                self.async_api._callbacks[request_id](result)

        # 替换异步请求方法
        self.async_api.request = mock_multiple_requests

        try:
            # 执行多个同步请求
            result1 = self.sync_wrapper.request("req-1", {"value": "数据1"})
            result2 = self.sync_wrapper.request("req-2", {"value": "数据2"})

            # 验证结果
            self.assertEqual(result1["request_id"], "req-1")
            self.assertEqual(result1["result"], "结果-数据1")
            self.assertIn("formatted_time", result1)
            
            self.assertEqual(result2["request_id"], "req-2")
            self.assertEqual(result2["result"], "结果-数据2")
            self.assertIn("formatted_time", result2)
            
        finally:
            # 恢复原始方法
            self.async_api.request = original_request


if __name__ == '__main__':
    unittest.main()
