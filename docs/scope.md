# MeterGate 首版范围

提供企业数据查询 API 的计量与结算平台。演示闭环为：创建企业和成员 → 创建套餐并订阅 → 生成 API Key → 调用演示数据接口 → 查询用量及剩余额度 → 关闭周期并生成账单 → 模拟支付 → 查询账单和审计记录。

## 首版范围

- 模块化单体；每租户一个订阅，企业管理员与普通成员两种角色。
- CNY 单币种、每月计费、整数次数计量；金额以整数分保存和计算，禁止用 float 计算金额。
- 套餐变更在下一周期生效，支付仅使用 mock。不处理真实资金、税务、退款、复杂优惠、跨币种结算或按比例补差价。
- 以 OpenAPI、演示脚本和轻量管理页面展示，不另建复杂前端。

## 固定计费与数据规则

以下是后续实现必须遵守的约定，第 01 天只固定规则，尚未实现计费业务。

1. 账单公式：`total_cents = base_fee_cents + successful_count * unit_price_cents`。成功调用才计量；`hard_limit` 为周期硬额度上限。
2. 数据库时间统一使用带时区的 UTC，月周期采用左闭右开的 `[start_at, end_at)`。按服务端 `received_at` 归属周期，`occurred_at` 仅供分析；迟到事件归入接收时的开放周期。
3. 周期开始时保存套餐价格与额度快照，历史账单按该快照计算；后续编辑套餐不能修改历史费用。
4. 租户来自已验证 JWT 的成员关系或 API Key，不能信任客户端提供的租户标识。成员访问资源时同时按资源 ID 与租户 ID 查询；首版实现应用层隔离，RLS 留待后续扩展。
5. 用量幂等键为 `(tenant_id, event_id)`：相同键、相同内容返回原结果快照；相同键、不同内容返回 HTTP 409。验证身份与 scope 后先查已完成事件，历史重放不要求旧周期仍开放，也不再次扣额度。
6. 用量事件插入和额度条件更新在同一数据库事务内完成，依赖唯一约束与 `UPDATE ... WHERE used + quantity <= hard_limit RETURNING ...` 处理并发，禁止先查余额再无条件写入。
7. 演示业务仅执行数据库内可回滚操作，业务成功、事件写入、额度扣减一起提交；失败一起回滚。未来调用外部服务时另行设计预留与确认协议。
8. 批量上报只允许带 `usage:write` 的可信集成密钥；演示 API 由服务端计量，客户端不能自行申报调用次数。
9. 周期关闭与新事件接收采用一致的行锁顺序。关闭后不再写入旧周期；后续实现 `resolve_open_period(now)`，在锁内完成到期周期轮转，不依赖定时扫描恰好及时执行。
10. 事务 Outbox 使用至少一次投递，消费者必须幂等；不承诺数据库与队列之间严格 exactly-once。

## 第 01 天交付边界

第 01 天交付为配置、应用入口、lifespan 和 `/health/live`，以及依赖锁文件、Ruff 与 pytest；该阶段不连接数据库、Redis 或支付商。

数据库、迁移、用户权限及计费模块按计划逐步实现；预留目录不代表业务功能已完成。第 01 天复验结果见 [验收记录](day01-acceptance.md)。

2026-10-15，第 02 天验收通过：实现 PostgreSQL/Redis 连接资源、请求会话、`/health/ready` 与 Alembic 版本基线，验证空库迁移和数据库停机/恢复。业务模型尚未实现。当前状态以根目录 progress.md 为准。

详细计划见仓库的 `docs/plan.md`，当前进度仅记录在根目录 `progress.md`。

资源生命周期采用 [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)；配置使用 [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)。
