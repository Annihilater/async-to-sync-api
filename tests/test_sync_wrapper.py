import asyncio
import unittest
from typing import Dict, Any

from main import AsyncAPI, SPI, SyncAPIWrapper, format_time_utc8, CallbackResult


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

    def test_format_time_utc8(self) -> None:
        """
        测试UTC+8时间格式化函数
        执行命令:
        python -m unittest tests.test_sync_wrapper.TestSyncAPIWrapper.test_format_time_utc8
        """
        # 测试指定时间戳
        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        formatted_time = format_time_utc8(timestamp)
        self.assertEqual(formatted_time, "2021-01-01 08:00:00")  # UTC+8

        # 测试当前时间
        current_formatted = format_time_utc8()
        self.assertIsInstance(current_formatted, str)
        self.assertEqual(len(current_formatted), 19)  # YYYY-MM-DD HH:MM:SS

    def test_multiple_callbacks(self) -> None:
        """
        测试多个回调的情况
        执行命令:
        python -m unittest tests.test_sync_wrapper.TestSyncAPIWrapper.test_multiple_callbacks
        """
        # 模拟异步请求方法
        original_request = self.async_api.request

        async def mock_multiple_callbacks(request_id: str, data: Dict[str, Any]) -> None:
            # 检查回调表
            if request_id not in self.async_api._callbacks:
                return

            # 获取所有回调
            callbacks = self.async_api._callbacks.get(request_id, {})

            # 依次处理每个回调
            for callback_id, callback_func in list(callbacks.items()):
                # 不同回调不同延迟
                await asyncio.sleep(0.1)

                # 构造成功结果
                result = CallbackResult.create_success(
                    callback_id,
                    {
                        "request_id": request_id,
                        "result": f"测试结果-{data.get('value', '')}-{callback_id}"
                    }
                ).to_dict()

                # 触发回调
                callback_func(result)

        # 替换异步请求方法
        self.async_api.request = mock_multiple_callbacks

        try:
            # 执行同步请求，等待4个回调
            results = self.sync_wrapper.request(
                "test-multiple",
                {"value": "测试数据"},
                callback_count=4,
                timeout=2.0
            )

            # 验证结果
            self.assertEqual(len(results), 4)

            # 验证所有回调都是成功的
            for result in results:
                self.assertEqual(result["status"], CallbackResult.SUCCESS)
                self.assertIn("callback_id", result)
                self.assertIn("formatted_time", result)
                self.assertIn("data", result)

                # 验证数据
                data = result["data"]
                self.assertEqual(data["request_id"], "test-multiple")
                self.assertIn("test-multiple-cb-", data["result"])

        finally:
            # 恢复原始方法
            self.async_api.request = original_request

    def test_mixed_callback_results(self) -> None:
        """
        测试混合成功、失败和超时的回调结果
        执行命令:
        python -m unittest tests.test_sync_wrapper.TestSyncAPIWrapper.test_mixed_callback_results
        """
        # 模拟异步请求方法
        original_request = self.async_api.request

        async def mock_mixed_callbacks(request_id: str, data: Dict[str, Any]) -> None:
            # 检查回调表
            if request_id not in self.async_api._callbacks:
                return

            # 获取所有回调
            callbacks = self.async_api._callbacks.get(request_id, {})

            # 记录已处理的回调
            processed = 0

            # 依次处理每个回调
            for callback_id, callback_func in list(callbacks.items()):
                # 根据回调ID设置不同的结果类型
                if processed % 3 == 0:  # 成功
                    await asyncio.sleep(0.1)
                    result = CallbackResult.create_success(
                        callback_id,
                        {
                            "request_id": request_id,
                            "result": f"成功-{callback_id}"
                        }
                    ).to_dict()
                    callback_func(result)
                elif processed % 3 == 1:  # 失败
                    await asyncio.sleep(0.2)
                    result = CallbackResult.create_failure(
                        callback_id,
                        f"测试错误-{callback_id}",
                        {"request_id": request_id}
                    ).to_dict()
                    callback_func(result)
                else:  # 超时 - 不触发回调
                    pass

                processed += 1

        # 替换异步请求方法
        self.async_api.request = mock_mixed_callbacks

        try:
            # 执行同步请求，等待6个回调
            results = self.sync_wrapper.request(
                "test-mixed",
                {"value": "测试数据"},
                callback_count=6,
                timeout=1.0
            )

            # 验证结果
            self.assertEqual(len(results), 6)

            # 统计不同类型的结果
            success_count = sum(1 for r in results if r["status"] == CallbackResult.SUCCESS)
            failure_count = sum(1 for r in results if r["status"] == CallbackResult.FAILURE)
            timeout_count = sum(1 for r in results if r["status"] == CallbackResult.TIMEOUT)

            # 验证每种类型都有
            self.assertGreater(success_count, 0)
            self.assertGreater(failure_count, 0)
            self.assertGreater(timeout_count, 0)
            self.assertEqual(success_count + failure_count + timeout_count, 6)

        finally:
            # 恢复原始方法
            self.async_api.request = original_request


if __name__ == '__main__':
    unittest.main()
