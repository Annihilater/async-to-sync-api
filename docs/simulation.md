# 异步回调模拟行为说明

在本项目中，我们模拟了异步API的行为和回调结果，为了方便理解和演示，实现了确定性的模拟策略。

## 模拟策略

### 1. 固定的回调行为

为了让演示和测试更加可控，对不同的请求ID使用了固定的行为模式：

#### req-001: 正常请求，部分成功部分失败

- 该请求注册4个回调
- 回调延迟递增：1秒, 2秒, 3秒, 4秒 (最后一个回调可能会出现竞争条件)
- 回调结果固定：
    - 第1个回调：**失败**
    - 第2个回调：**成功**
    - 第3个回调：**成功**
    - 第4个回调：**失败** (可能显示为超时，取决于具体执行情况)

```python
if request_id.startswith("req-001"):
    # 对req-001，使用固定的延迟模式
    delay = 1 + index  # 1, 2, 3, 4秒
    # 固定的成功/失败模式: 1和4失败，2和3成功
    should_fail = (index == 0 or index == 3)

    # 确保第4个回调的延迟不超过超时时间 (10秒)
    if index == 3:  # 第4个回调
        delay = min(delay, 8)  # 确保不超过10秒超时
```

**注意**：第4个回调可能会导致竞争条件 - 如果超时处理先发生，回调会被标记为超时，然后实际回调才到达。这是异步系统中的真实场景，展示了超时处理的复杂性。

#### req-002: 超时请求，部分回调不会响应

- 该请求注册4个回调
- 回调延迟设置：
    - 第1个回调：1秒（能在超时前完成）
    - 第2-4个回调：3秒（超过2秒超时限制）
- 由于超时设置为2秒，只有第1个回调能在超时前完成
- 第2-4个回调会被标记为超时

```python
elif request_id.startswith("req-002"):
# 对req-002，设置较长延迟使大部分回调超时
delay = 1 if index == 0 else 3  # 第一个回调1秒，其余3秒
# 只有第一个成功，其他由于超时会失败
should_fail = False
```

#### test-*: 测试专用请求

- 为单元测试设计的请求类型
- 所有回调使用0.1秒的短延迟确保测试快速运行
- 不同的测试用例可能设置不同的成功/失败模式

```python
elif request_id.startswith("test"):
# 测试用例使用短延迟
delay = 0.1
# 根据测试需求设置失败模式
should_fail = False
```

#### 其他请求

- 对于其他请求ID，使用基于回调ID的确定性随机模式
- 延迟根据回调ID的最后一个字符确定（1-3秒）
- 20%的随机失败率

```python
else:
# 其他请求使用随机模式
delay = 1 + (ord(callback_id[-1]) % 3)
should_fail = (ord(callback_id[-1]) % 5 == 0)
```

### 2. 超时处理

当使用超时时间较短的请求时（例如req-002使用2秒超时），一些回调可能无法在超时前完成，这种情况下：

1. 系统会等待超时时间结束
2. 已收到的回调结果会被正常处理
3. 未收到的回调会被标记为`TIMEOUT`状态
4. 所有回调结果（成功、失败和超时）都会被收集并返回

```python
# 处理未返回的回调（超时）
received_callback_ids = {result.get("callback_id") for result in results}
for callback_id in callback_ids:
    if callback_id not in received_callback_ids:
        timeout_result = CallbackResult.create_timeout(callback_id).to_dict()
        self.spi.on_response(timeout_result)
        results.append(timeout_result)
```

## 运行结果解释

由于使用了确定性的模拟策略，每次运行的结果应该是一致的：

### req-001（10秒超时）

每次运行应该看到：

- 4个回调全部完成
- 2个成功、2个失败
- 0个超时

### req-002（2秒超时）

每次运行应该看到：

- 只有第1个回调能在超时前完成（1个成功）
- 第2-4个回调会超时（3个超时）

## 修改模拟行为

如果需要修改模拟行为，可以在`AsyncAPI.request`方法中调整以下内容：

1. 延迟时间：调整`delay`变量
2. 成功/失败条件：调整`should_fail`标志
3. 超时时间：在`SyncAPIWrapper.request`调用时调整`timeout`参数

## 2. 竞争条件与超时处理

在异步系统中，超时和实际回调之间可能存在竞争条件。这在我们的模拟中也有体现：

1. **超时先发生情况**：如果超时检测先执行，会将未收到的回调标记为超时。但是，这些回调可能在稍后到达。

2. **回调实际到达**：即使已经被标记为超时，如果回调最终还是到达了，我们仍然会看到其输出（虽然在结果统计中已经被计为超时）。

这种情况在第4个回调中最为明显，因为其延迟接近超时时间。这种现象展示了异步系统中的真实复杂性，特别是在处理超时机制时。

## 结果解释

每次运行时，您可能会看到：

### req-001（10秒超时）结果

- 第1个回调：总是**失败**（1秒后）
- 第2个回调：总是**成功**（2秒后）
- 第3个回调：总是**成功**（3秒后）
- 第4个回调：可能出现竞争条件
    - 先显示为**超时**
    - 然后可能显示实际的**失败**结果
    - 在结果统计中可能会计为超时或失败（取决于具体执行）

### req-002（2秒超时）结果

- 第1个回调：总是**成功**（1秒后到达）
- 第2-4个回调：总是**超时**（因为设置了只有2秒的超时）

## 超时处理机制

当等待多个回调结果时，系统会：

1. 等待直到超时或所有回调都返回
2. 对未收到的回调标记为超时
3. 汇总所有回调结果（成功、失败和超时）

```python
# 处理未返回的回调（超时）
received_callback_ids = {result.get("callback_id") for result in results}
for callback_id in callback_ids:
    if callback_id not in received_callback_ids:
        timeout_result = CallbackResult.create_timeout(callback_id).to_dict()
        self.spi.on_response(timeout_result)
        results.append(timeout_result)
```

## 结论

这种模拟方式有助于演示：

1. 异步系统中的成功/失败场景
2. 超时处理机制
3. 多回调结果的汇总策略
4. 竞争条件与实际执行顺序的不确定性

这些场景都是实际异步系统中会遇到的常见问题，通过这种模拟可以更好地理解如何设计健壮的异步到同步转换系统。 