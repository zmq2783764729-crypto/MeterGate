# MeterGate 首版范围

提供企业数据查询 API 的计量与结算平台，闭环为企业注册、套餐订阅、API Key、调用计量、额度控制、账单、模拟支付与审计。

- 采用模块化单体；金额存整数分，CNY 单币种，每月计费。
- 首版套餐下一周期变更，支付使用 mock；不处理真实资金、税务或跨币种结算。
- 关键设计为租户隔离、用量幂等、数据库条件扣减、周期条款快照与事务 Outbox。
- 当前骨架只提供配置、应用入口、lifespan 和 `/health/live`；不连接数据库、Redis 或支付商。
- 数据库、迁移、用户权限及计费模块按根目录计划逐步实现；预留目录不代表业务功能已完成。

详细计划见仓库的 `docs/plan.md`，当前进度仅记录在根目录 `progress.md`。

资源生命周期采用 [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)；配置使用 [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)。
