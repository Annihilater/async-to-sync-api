# 异步到同步API转换实现细节

## 设计目标

在实际开发中，我们经常需要将异步API封装为同步调用方式，主要有以下场景：

1. 将基于回调的异步API改造为同步调用
2. 将使用协程的异步API改造为普通函数调用
3. 保持API调用简单性同时隐藏异步实现细节
4. 同步收集多个异步回调的结果

## 核心功能组件

### 1. 时间格式化工具函数

`format_time_utc8`函数将时间戳转换为UTC+8时区的人类可读格式：

```python
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
```

### 2. 回调结果类

`CallbackResult`类用于统一处理回调结果，支持三种状态：成功、失败和超时。

```python
class CallbackResult:
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
        """将结果转换为字典"""
        # 包含回调ID、状态、数据、错误信息和时间信息
```

### 3. 异步API模型

`AsyncAPI` 类模拟了一个典型的异步API接口，更新为支持多回调：

```python
class AsyncAPI:
    def __init__(self):
        self._callbacks: Dict[str, Dict[str, Callable]] = {}

    def register_callback(self, request_id: str, callback_id: str, callback: Callable):

    # 注册指定请求ID和回调ID的回调函数

    def unregister_callback(self, request_id: str, callback_id: Optional[str] = None):

    # 注销回调函数，支持注销单个回调或整个请求的所有回调

    async def request(self, request_id: str, data: Dict[str, Any]):
# 发送异步请求
# 使用多回调处理机制
```

### 4. SPI回调接口

`SPI` 类模拟了回调接口，更新为处理不同类型的回调结果：

```python
class SPI:
    def on_response(self, result: Dict[str, Any]):
# 处理不同类型的回调响应（成功/失败/超时）
# 根据状态类型采取不同的处理方式
```

### 5. 同步封装实现

`SyncAPIWrapper` 类将异步API封装为同步调用方式，支持多回调收集：

#### 5.1 事件循环与线程

在独立线程中运行事件循环，避免阻塞主线程：

```python
def __init__(self, async_api: AsyncAPI, spi: SPI):
    self.loop = asyncio.new_event_loop()
    self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
    self.thread.start()


def _run_event_loop(self):
    asyncio.set_event_loop(self.loop)
    self.loop.run_forever()
```

#### 5.2 多回调的请求与响应收集

使用队列存储异步回调的结果，支持收集多个回调：

```python
def request(self, request_id: str, data: Dict[str, Any],
            callback_count: int = 4, timeout: float = 5.0) -> List[Dict[str, Any]]:
    # 创建结果队列和回调计数器
    result_queue = queue.Queue()
    callback_counter = {"count": 0}

    # 创建回调ID列表并注册回调
    callback_ids = [f"{request_id}-cb-{i + 1}" for i in range(callback_count)]
    for callback_id in callback_ids:
        self.async_api.register_callback(request_id, callback_id, callback)

    # 提交异步任务
    asyncio.run_coroutine_threadsafe(...)

    # 等待多个回调结果或超时
    # 收集已收到的结果
    # 为未响应的回调生成超时结果

    return results
```

#### 5.3 资源管理

确保资源被正确清理，避免内存泄漏：

```python
def close(self):
    self.loop.call_soon_threadsafe(self.loop.stop)
    self.thread.join(timeout=1.0)
```

## 使用多回调的优势

支持多回调模式有以下优势：

1. **并行处理**: 一个请求可以触发多个并行处理流程
2. **结果聚合**: 可以收集和聚合多个处理结果
3. **容错能力**: 即使部分回调失败或超时，仍能获取其他成功的结果
4. **灵活性**: 可以根据需要注册不同数量的回调

## 实现优势

该实现方案有以下优势：

1. **隐藏复杂性**: 调用者不需要了解异步编程细节
2. **简化代码**: 避免编写复杂的异步控制流程
3. **兼容性**: 可与同步代码无缝集成
4. **超时控制**: 避免无限等待，提高系统健壮性
5. **资源管理**: 适当处理线程和事件循环资源
6. **结果类型统一**: 通过`CallbackResult`类统一处理成功/失败/超时情况

## 适用场景

此模式特别适用于以下场景：

1. 需要在同步代码中调用异步API
2. 需要简化异步API的使用方式
3. 需要将第三方异步库适配到同步代码架构中
4. 在不支持异步的环境中使用异步API
5. 一个请求需要触发多个回调并收集结果的场景

## 注意事项

在使用此模式时需要注意：

1. 合理设置超时时间，避免长时间阻塞
2. 妥善处理异常情况，包括网络错误、超时等
3. 关注资源管理，确保线程和事件循环被正确释放
4. 避免在高并发场景过度使用，可能造成线程资源耗尽
5. 回调数量不宜过多，以免影响性能 