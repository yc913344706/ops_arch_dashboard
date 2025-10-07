## 配置驱动的告警处理流程

以 `response_time_slow` 规则为例，详细说明从YAML配置到实际告警的处理流程：

### 1. 配置加载
- `AlertConfigParser` 读取 `alert_rules.yaml` 文件
- 将 `response_time_slow` 规则解析为 `AlertRule` 对象

### 2. 定时任务触发
- Celery 按 `check_interval`（如 "10m"）执行 `check_all_alerts` 任务
- 任务获取所有启用的告警规则

### 3. 数据获取和聚合
- 根据 `time_window`（如 "5m"）获取最近5分钟的健康记录
- 根据 `aggregation`（如 "avg"）计算聚合值（如平均响应时间）

### 4. 条件评估
- 构建评估上下文，包含节点信息、聚合值等数据
- 评估 `condition`（如 "avg_response_time > 1000"）
- 使用 `extract_threshold_from_condition` 函数从条件中提取阈值（1000）

### 5. 告警判断和创建
- 如果条件评估为 `True`，使用 `message` 模板格式化告警消息
- 调用 `create_or_update_alert` 创建或更新告警记录
- 确保告警唯一性，避免重复创建
- 新告警状态默认为"开启(OPEN)"，等待运维处理

### 6. 告警状态管理
- **开启(OPEN)**：告警触发后的初始状态
- **已确认(ACKNOWLEDGED)**：运维人员手动确认告警后改变状态，表示已注意到此告警
- **已关闭(CLOSED)**：问题解决或手动关闭后改变状态，表示告警结束
- **自动状态转换**：当监控数据恢复正常时，系统自动将相关告警状态改为"已关闭"

### 7. 完整数据流
```
YAML配置 → AlertRule对象 → check_all_alerts任务 → 
获取时间窗口数据 → 计算聚合值 → 提取阈值 → 
评估条件 → 格式化消息 → 创建/更新告警 → 存储 → 前端展示 → 
运维处理（确认/关闭）→ 状态管理 → 自动恢复检测
```

通过这种方式，实现了完全配置驱动的告警系统，无需修改代码即可调整告警策略。