# MeterGate｜企业服务计量与结算平台：30 天开发计划

> 方向：FastAPI 后端工程。版本：v1.0。编制日期：2026-10-09。
> 本文是实施计划，任务尚未执行；验收指标是目标，不是已经取得的性能结果。

## 1. 项目定位与完成目标

**项目名称：MeterGate（企业服务计量与结算平台）。**

业务场景：一家提供数据查询 API 的公司，向不同企业销售服务。企业拥有成员、API Key 和套餐；平台记录服务调用量，限制额度，按“周期基础费 + 成功调用量 × 单价”生成账单，通过模拟支付回调确认付款，并保留操作记录。

参考 [Polar](https://github.com/polarsource/polar) 的商业业务划分和后端实现，独立编写一个范围可控的项目。MeterGate 的功能、文件名和实现顺序均为本计划设计，不是 Polar 现有代码的说明。阅读参考代码要回答一个具体问题，再回到自己的实现；不要求完整复制或运行 Polar。

**最终演示闭环：**创建企业 → 创建套餐并订阅 → 生成 API Key → 调用演示数据接口 → 查看用量及剩余额度 → 关闭计费周期并生成账单 → 模拟支付 → 查询账单和审计记录。

重点展示：租户隔离、异步数据库访问、事务边界、幂等处理、并发额度扣减、可靠后台任务、回调验签、账单可复算、部署与故障排查。

## 2. 时间、前置条件和范围

- 30 个工作日，每天约 6–8 小时；两个项目顺序开发时合计约 60 个工作日，不是 60 个自然日。
- 假设已掌握 Python、HTTP、基础 SQL、Git 和 FastAPI 基本路由。尚不熟悉这些内容时，先补基础，并允许复杂任务拆成两天。
- 每天建议：30–45 分钟阅读与设计、4–5 小时编码、1–1.5 小时针对性验证、30 分钟记录与提交。
- 主线只做一个币种 CNY、每月计费、按整数次数计量、企业管理员与普通成员两类角色，以及本地模拟支付。货币金额以整数分存储，禁止用 float 计算金额。
- 首版只允许套餐变更在下一周期生效。税务、真实收款、退款、复杂优惠、跨币种结算、按比例补差价均放在主线之后。
- 前端以 OpenAPI 文档、演示脚本和轻量管理页面为主；不另建复杂 React 项目。采用模块化单体，先证明业务正确性。
- 外部真实支付接入属于后续扩展；主线不需要支付商户账号，也不处理真实资金。

## 3. 固定技术路线

| 层次 | 选择 | 用途 |
|---|---|---|
| API | FastAPI、Pydantic | 路由、参数验证、接口文档 |
| 数据库 | PostgreSQL、SQLAlchemy 2.x、Alembic | 事务、约束、迁移 |
| 缓存与队列 | Redis、Dramatiq | 限流、后台任务；额度真值保存在 PostgreSQL |
| 登录 | 密码哈希、短期 JWT | 用户认证；成员身份由数据库校验 |
| 测试 | pytest、HTTPX、真实测试 PostgreSQL | 接口、事务、并发和租户隔离验证 |
| 运维 | Docker Compose、结构化日志、Prometheus | 启动、追踪、业务指标 |
| 工程工具 | uv、Ruff、GitHub Actions | 锁依赖、静态检查、持续集成 |

第 1 天确定能安装并相互兼容的依赖版本，提交锁文件；不要在开发期间无理由追逐最新版。FastAPI 用 lifespan 管理资源；同一 AsyncSession 不在多个并发任务之间共享。相关依据见 [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/) 与 [SQLAlchemy 异步使用说明](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)。

## 4. 代码目录约定

以下路径相对于本仓库根目录。实际实现进度以根目录 progress.md 为准。

```text
metergate/
  pyproject.toml
  uv.lock
  .env.example
  app/
    main.py
    api/router.py
    core/{config,security,errors,logging}.py
    db/{base,session}.py
    dependencies/{auth,tenant,permissions}.py
    middleware/request_context.py
    modules/
      auth/
      tenants/
      api_keys/
      catalog/
      subscriptions/
      metering/
      billing/
      payments/
      audit/
      demo/
    integrations/payments/{base,mock}.py
    workers/{broker,outbox,tasks}.py
    observability/metrics.py
    templates/dashboard.html
  migrations/versions/
  tests/{unit,integration,concurrency}/
  scripts/
  deploy/
  docs/
```

每个业务模块按需要包含 `models.py`、`schemas.py`、`repository.py`、`service.py`、`router.py`。路由负责 HTTP 和验证，service 编排业务及事务，repository 执行查询。不要为了目录整齐创建没有用途的抽象层。

## 5. 先固定业务规则和数据边界

### 5.1 核心表

| 表 | 关键字段及约束 |
|---|---|
| users | id、email 唯一、password_hash、is_active |
| tenants | id、name、status |
| memberships | tenant_id、user_id、role；二者联合唯一 |
| api_keys | tenant_id、key_hash、prefix、scopes、expires_at、revoked_at |
| plans / plan_versions | 套餐标识、版本、base_fee_cents、unit_price_cents、hard_limit、is_active |
| subscriptions | tenant_id、current_plan_version_id、pending_plan_version_id、status、cancel_at_period_end；每租户首版仅一个订阅 |
| billing_periods | tenant_id、subscription_id、start_at、end_at、state、条款快照；时间区间采用 [start, end) |
| quota_buckets | tenant_id、period_id、metric、used、hard_limit；三者联合唯一 |
| usage_events | tenant_id、event_id、period_id、metric、quantity、occurred_at、received_at、payload_hash、result_snapshot；tenant_id + event_id 唯一 |
| invoices / invoice_items | tenant_id、period_id 唯一、status、费用快照、total_cents、内容校验值 |
| payments | tenant_id、invoice_id、provider_payment_id 唯一、amount_cents、currency、status |
| webhook_events | provider、provider_event_id 联合唯一、payload_hash、received_at、processing_status |
| outbox_events | 事件类型、聚合 ID、payload、attempts、next_attempt_at、published_at |
| audit_logs | tenant_id、actor_id、action、resource_id、request_id、redacted_detail、created_at |

业务表中的 tenant_id 使用外键和必要索引。系统套餐是平台公共资源，不能把平台管理权限和租户管理权限混用。

### 5.2 必须保持的约定

1. 从已验证 JWT 对应的成员关系或 API Key 解析租户；客户端传来的 tenant_id 只是请求目标，不能直接成为授权依据。
2. 成员访问资源时同时按资源 ID 和租户 ID 查询。首版采用应用层隔离；PostgreSQL RLS 可作为后续加固，不能声称已经具备。
3. 调用事件幂等键是 `(tenant_id, event_id)`；同一键、相同内容返回原结果，同一键、不同内容返回 409。身份和 scope 验证后先查询已完成事件，历史重放不重新要求旧周期仍开放；原响应的业务字段写入 result_snapshot。
4. 用量事件插入与条件额度更新位于同一事务。使用数据库唯一约束及 `UPDATE ... WHERE used + quantity <= hard_limit RETURNING ...` 处理竞争；不能只做“先查余额再写”。
5. 演示业务只执行数据库内的可回滚写入，业务成功、事件写入和额度扣减同事务提交。未来接入外部服务时需要另行设计预留与确认协议。
6. API 批量上报只允许有 `usage:write` 的可信集成密钥。演示 API 采用服务端计量，防止客户端自行少报。
7. 首版按服务端接收时间归属周期，occurred_at 只作分析信息；迟到事件归入接收时的开放周期。这个规则要在接口文档中明确。
8. 所有数据库时间使用带时区 UTC；页面可转换为中国时间。周期关闭与事件接收使用一致的行锁顺序，关闭后禁止向旧周期写入。第 20 天统一实现 resolve_open_period(now)：首次新事件遇到到期周期时，在锁内完成轮转，避免依赖运维扫描恰好及时执行。
9. 周期价格和额度来自开始时保存的套餐快照；历史账单不随套餐编辑变化。
10. Outbox 采用至少一次投递，消费者必须幂等；首版不声称跨数据库与队列实现严格 exactly-once。

## 6. 每日开发任务

### 第 01 天｜搭建可运行骨架

**目标：**一个能启动、能检查、能被测试的 FastAPI 服务。

- 文件：`pyproject.toml`、`.env.example`、`app/main.py`、`app/core/config.py`、`app/api/router.py`。
- 编码：实现 `Settings`、`create_app()`、`lifespan()` 和 `GET /health/live`；锁定依赖，配置 Ruff、pytest；环境变量中保留 PostgreSQL、Redis 和 JWT 配置占位。
- 记录：`docs/scope.md` 写明项目闭环、首版范围和上面的计费规则。
- 验收：开发命令启动服务，健康接口返回 200，`uv run ruff check .` 通过；不把真实密钥提交到仓库。

### 第 02 天｜数据库连接与首次迁移

**目标：**可靠地建立和释放异步数据库连接。

- 文件：`app/db/base.py`、`app/db/session.py`、`migrations/env.py`、`deploy/compose.dev.yml`。
- 编码：创建 `async_sessionmaker`、`get_session()`；明确 service 负责事务提交；配置 Alembic；开发 Compose 启动 PostgreSQL 和 Redis。
- 编码：新增 `GET /health/ready`，检查数据库与必需组件；连接失败返回 503，不暴露连接凭据。
- 验收：空数据库完成迁移；停掉 PostgreSQL 时 ready 失败、live 仍可用；退出服务后连接池关闭。

### 第 03 天｜统一错误、请求标识与接口规范

**目标：**后续接口拥有一致的错误响应。

- 文件：`app/core/errors.py`、`app/core/logging.py`、`app/middleware/request_context.py`。
- 编码：定义 `DomainError(code, message, status_code)`；注册验证异常与领域异常处理；每次请求生成 request_id，通过响应头和日志关联。
- 约定：成功响应直接使用业务 Schema；错误响应包含 `code/message/request_id`；分页采用 `items/next_cursor`，不要再套多层万能包装。
- 验收：无效参数、缺少认证和未知错误分别得到合理状态码；日志不输出密码、JWT 或 API Key。

### 第 04 天｜用户注册与密码登录

**目标：**用户能够注册和登录。

- 文件：`app/modules/auth/{models,schemas,repository,service,router}.py`，用户表迁移。
- 编码：实现 `register_user()`、`authenticate_user()`、`POST /v1/auth/register`、`POST /v1/auth/login`；使用成熟密码哈希库和短期 JWT。
- 编码：JWT 校验算法白名单、issuer、audience、过期时间；响应禁止返回 password_hash。
- 验收：重复邮箱返回 409；错误密码、过期或伪造 token 返回 401；哈希不是明文或简单 SHA 摘要。

### 第 05 天｜企业与成员关系

**目标：**用户能创建企业并成为管理员。

- 文件：`app/modules/tenants/{models,schemas,repository,service,router}.py`，租户与成员迁移。
- 编码：`create_tenant_with_owner()` 在同一事务内写入企业与管理员成员；实现 `POST /v1/tenants`、`GET /v1/tenants`。
- 编码：用户列表只返回自己加入的企业；成员关系加联合唯一约束。
- 验收：企业创建失败不会留下半条成员关系；A 用户看不到 B 用户所属企业。

### 第 06 天｜租户上下文与角色权限

**目标：**建立所有业务接口使用的授权入口。

- 文件：`app/dependencies/{auth,tenant,permissions}.py`、`app/modules/tenants/router.py`。
- 编码：`get_current_user()`、`resolve_membership(tenant_id)`、`require_role()`；新增成员添加、成员列表接口；首版添加已注册用户，不做邮件邀请。
- 编码：所有租户资源查询传入 `TenantContext`；管理员管理成员，普通成员只能读授权业务数据；禁止删除最后一个管理员。
- 验收：修改 URL 中 tenant_id 不能越权；普通成员无法添加管理员；保留一组跨租户访问集成测试。

### 第 07 天｜API Key 生命周期

**目标：**企业创建并撤销机器访问凭据。

- 文件：`app/modules/api_keys/{models,schemas,repository,service,router}.py`、密钥表迁移。
- 编码：`create_api_key()` 生成高熵随机 token，数据库仅保存摘要与显示前缀；实现创建、列表、撤销接口。
- 编码：支持 `demo:read`、`usage:write` 两种 scope、过期时间和已撤销状态；完整密钥仅在创建响应中出现一次。
- 验收：列表看不到完整密钥；撤销立即生效；scope 不匹配返回 403；密钥不进入日志。

### 第 08 天｜套餐与不可变版本

**目标：**把价格定义和历史账单隔离。

- 文件：`app/modules/catalog/{models,schemas,repository,service,router}.py`、`scripts/seed_catalog.py`。
- 编码：建立 Plan 与 PlanVersion；实现公开套餐查询；平台套餐维护通过管理脚本完成，不复用租户管理员接口。
- 编码：`create_plan_version()` 只新增版本；校验金额非负、hard_limit 大于零；准备基础、专业两个演示套餐。
- 验收：修改套餐生成新版本，旧版本仍可查询；负数价格、浮点金额和非法额度被拒绝。

### 第 09 天｜订阅状态和周期快照

**目标：**创建企业的第一个订阅和计费周期。

- 文件：`app/modules/subscriptions/{models,schemas,repository,service,router}.py`、订阅与周期迁移。
- 编码：`activate_subscription()` 原子创建订阅、开放周期和套餐条款快照；实现 `POST /v1/tenants/{id}/subscription`、订阅查询。
- 编码：`period_start/end` 统一 UTC 与半开区间；同一租户首版只允许一个订阅。
- 验收：重复创建被数据库与业务共同阻止；周期长度及月末边界正确；订阅读取不越权。

### 第 10 天｜下周期变更与取消

**目标：**实现清晰、可解释的订阅生命周期。

- 文件：`app/modules/subscriptions/service.py`、`schemas.py`、`router.py`、`tests/unit/test_subscription_transitions.py`。
- 编码：`schedule_plan_change()`、`cancel_at_period_end()`；变更写 pending 字段，取消写到期标记；当前周期费用和额度保持快照。
- 编码：非法状态转移返回 409；到期后取消的订阅不可消费；将状态转换表写入 `docs/subscription_states.md`。
- 验收：预约升级不改变当期价格；重复取消返回确定结果；已取消订阅不能直接恢复为 active。

### 第 11 天｜用量事件和请求契约

**目标：**建立后续幂等与计量的数据基础。

- 文件：`app/modules/metering/{models,schemas,repository}.py`、用量事件与额度桶迁移。
- 编码：定义 `UsageIn(event_id, metric, quantity, occurred_at)`、`UsageResult`；允许首版 metric 为 `data_query`，quantity 为正整数且有限上界。
- 编码：新增 `(tenant_id,event_id)` 唯一约束、周期查询索引；实现规范化请求摘要 `canonical_payload_hash()`；额度桶由订阅激活初始化。
- 验收：同租户重复键不能写两次，不同租户可使用相同 event_id；非法 metric、负数与超大数量被拒绝。

### 第 12 天｜事件接收与幂等结果

**目标：**接收可信集成方的用量上报。

- 文件：`app/modules/metering/{service,router}.py`、`tests/integration/test_usage_idempotency.py`。
- 编码：`ingest_usage()`、`POST /v1/usage/events`；以 API Key 解析租户，要求 `usage:write`；事务中保存事件并更新额度。
- 编码：重复请求返回原事件与原处理结果，标明 replayed；相同 event_id 的不同业务载荷返回 409。数据库冲突处理后必须恢复事务状态再查询原记录。
- 验收：同一事件串行发送 3 次仅产生一条用量记录、一次扣减；冲突内容不会改变原数据。

### 第 13 天｜并发扣减与事务回滚

**目标：**让第 12 天逻辑在并发下仍然正确。

- 文件：`app/modules/metering/repository.py`、`service.py`、`tests/concurrency/test_quota.py`。
- 编码：使用条件 UPDATE 获取新 used；事务内插入事件、锁定开放周期、扣减额度；统一锁顺序为订阅/周期 → 额度桶。
- 编码：在订阅/周期锁内写新事件并更新额度；额度不足返回明确领域错误；整个事务回滚，不能留下“已扣额度但无事件”或“事件已记录但未扣额度”。读取并返回 result_snapshot，确保重放不会返回新变化的余额。
- 验收：准备额度 100，200 个不同 event_id 并发消费各 1 次；应有 100 次成功、used=100、100 条事件。并发重放同一键仍只扣一次。

### 第 14 天｜接入服务端计量的演示 API

**目标：**展示真实请求驱动计量，而不是单独手动填数字。

- 文件：`app/modules/demo/{models,service,router}.py`、`scripts/demo_requests.py`。
- 编码：`POST /v1/demo/data-query` 接收查询条件与 Idempotency-Key；要求 `demo:read` scope；演示业务结果、usage_event 和 quota 更新同事务保存。
- 编码：保存结果摘要供重放；同键不同查询返回 409；模拟失败在提交前触发，额度与结果一起回滚。
- 验收：成功查询扣一次，重试返回原结果，失败查询不扣额度，额度不足时不创建业务结果。

### 第 15 天｜用量查询与分页

**目标：**企业能查看当前消耗和历史事件。

- 文件：`app/modules/metering/{schemas,repository,service,router}.py`。
- 编码：`GET /v1/tenants/{id}/usage/summary` 与 `/usage/events`；支持周期、时间范围、metric 条件和游标分页；列表只暴露必要字段。
- 编码：摘要包含 used、hard_limit、remaining 和费用估算；估算标明非正式账单；边界校验限制最大查询范围。
- 验收：连续翻页无重复；估算遵循周期价格快照；A 企业无法读取 B 企业事件。

### 第 16 天｜Redis 限流与缓存边界

**目标：**保护接口，同时保留数据库计量的正确性。

- 文件：`app/modules/api_keys/rate_limit.py`、`app/core/config.py`、`tests/integration/test_rate_limit.py`。
- 编码：Lua 脚本或原子 Redis 操作实现按 API Key 的固定窗口限流；超限返回 429 与 Retry-After。
- 编码：限流与硬额度分开；Redis 故障时受限业务接口按明确配置返回 503，不能静默绕过；数据库 quota 不以 Redis 作为账本。
- 验收：窗口内请求数量受控，下一窗口恢复；多个 API 进程共用限流状态；Redis 断开不造成额度错误。

### 第 17 天｜审计记录

**目标：**可以回答谁在什么时候修改了关键业务资源。

- 文件：`app/modules/audit/{models,repository,service,router}.py`、审计表迁移。
- 编码：`record_audit()` 接入成员变更、密钥撤销、订阅变更与周期关闭；关键变更和审计在同一数据库事务中提交。
- 编码：详情脱敏，不保存完整 token、密码或回调签名；提供管理员可见的分页查询。
- 验收：关键变更可追溯 request_id；事务失败不产生成功审计；普通成员无法查询管理审计。

### 第 18 天｜事务 Outbox

**目标：**避免数据库提交成功但后台任务丢失。

- 文件：`app/workers/outbox.py`、`app/modules/billing/events.py`、Outbox 表迁移。
- 编码：`enqueue_domain_event(session, ...)` 在业务事务内写 outbox；实现批量扫描、`FOR UPDATE SKIP LOCKED`、attempts 与 next_attempt_at。
- 编码：明确“发布后、标记前崩溃会重投”；消费者以后用业务唯一键去重。先用可替换 publisher 验证，不依赖真实队列。
- 验收：业务回滚不会留下事件；扫描器并发工作不重复领取同一批；发布失败保留可重试事件。

### 第 19 天｜Dramatiq Worker 与可靠重试

**目标：**把 Outbox 接到真实后台执行。

- 文件：`app/workers/{broker,tasks,outbox}.py`、`deploy/compose.dev.yml`。
- 编码：配置 Redis broker；Worker 采用独立同步 SQLAlchemy Session 和 psycopg 连接，不复用 API 的 AsyncSession；publisher 发送事件 ID，actor 从数据库取业务载荷。
- 编码：限制重试次数、指数退避、失败记录；outbox 常驻轮询进程独立启动，避免把可靠任务放进 FastAPI BackgroundTasks。
- 验收：关闭 Worker 后提交的事件在恢复后得到执行；杀死消费者并重启不会重复产生业务结果。

### 第 20 天｜周期关闭与续期

**目标：**完成一个稳定的结算边界。

- 文件：`app/modules/subscriptions/period_service.py`、`app/workers/tasks.py`、`scripts/close_period.py`。
- 编码：`close_period()` 按统一锁顺序关闭旧周期；写结算 outbox；根据 pending 套餐及取消标记创建下一开放周期和额度桶，周期重叠由约束/锁检查阻止。
- 编码：新增 `resolve_open_period(now)`，与接收新事件共用周期轮转逻辑；提供受控命令扫描没有新请求的到期租户，可后续加定时器。演示加速使用显式测试时钟，不能由公网请求任意修改系统时间。
- 验收：并发关闭同周期只创建一个新周期和一条结算事件；关闭后迟到上报归属下一开放周期；取消到期后无法继续使用。

### 第 21 天｜账单模型与确定性计价

**目标：**用纯函数计算可复核的费用。

- 文件：`app/modules/billing/{models,schemas,calculator}.py`、账单迁移、`tests/unit/test_calculator.py`。
- 编码：`calculate_invoice(snapshot, total_quantity)` 输出基础费、用量费、总额及计算明细；金额始终使用整数分；仅消费成功且已提交的事件参与计算。
- 编码：invoice_items 保存数量、单价、行金额和套餐版本；invoice 与 period 一对一。
- 验收：准备 5 组固定数据，手算与函数一致；零用量仍正确收基础费；历史套餐价格变化不影响结果。

### 第 22 天｜异步生成账单与查询

**目标：**将已关闭周期转成不可变账单。

- 文件：`app/modules/billing/{repository,service,router}.py`、`app/workers/tasks.py`。
- 编码：`generate_invoice(period_id)` 只处理已关闭周期，聚合事件并保存快照；Worker 重投时查询并返回原账单；不覆盖已生成内容。
- 编码：实现账单列表、详情接口；账单状态采用 open/paid/void，void 预留但首版不开放作废操作。
- 验收：同一周期任务执行 3 次只生成一张账单；用量明细能复算账单；跨租户账单读取失败。

### 第 23 天｜模拟支付适配器

**目标：**准备与实际支付提供方解耦的接口。

- 文件：`app/integrations/payments/{base,mock}.py`、`app/modules/payments/{models,schemas,service,router}.py`。
- 编码：定义 `PaymentProvider.create_checkout()`、`verify_webhook()`；mock 创建支付会话，返回模拟页面/事件参数；支付会话与账单绑定。
- 编码：创建会话需要管理员权限；记录 expected_amount 与 CNY；模拟事件只能由本地脚本/开发页面生成，不开放任意“付款成功”管理员按钮。
- 验收：已支付账单不重复创建有效付款；请求不能修改应付金额；适配器可被确定性 fake 替换测试。

### 第 24 天｜回调验签、幂等和状态变更

**目标：**付款通知可靠改变账单状态。

- 文件：`app/modules/payments/{webhook_service,router}.py`、`scripts/send_mock_webhook.py`、回调事件表迁移。
- 编码：`POST /v1/webhooks/payments/mock` 按原始 body + timestamp 验 HMAC，限制时间偏差，使用常量时间比较；事件唯一键和摘要控制重放。
- 编码：事务内核对 payment、invoice、金额、币种和提供方标识，合法成功事件才将账单改为 paid；账单付款后，晚到 pending/failed 事件不能回退状态。
- 验收：重复成功回调 3 次只处理一次；篡改载荷、错误签名、金额不符和乱序失败事件均不造成错误入账。

### 第 25 天｜对账与失败任务处理

**目标：**发现并修复可确定的内部异常。

- 文件：`app/modules/billing/reconciliation.py`、`scripts/reconcile_period.py`、`scripts/retry_failed_jobs.py`。
- 编码：`reconcile_period()` 比较事件数量合计、quota.used、invoice_items 与账单金额；产出差异报告；不能自动修改已经支付的账单。
- 编码：重放失败事件走原幂等入口；权限受控的运维脚本支持 dry-run，记录审计。模拟支付对账仅核对 mock 数据，不声称验证真实银行流水。
- 验收：人为构造一条额度或账单差异能被报告；重复重试不会重复收费；无差异周期返回一致结果。

### 第 26 天｜日志、指标与故障定位

**目标：**从运行数据定位一个失败请求和一个积压任务。

- 文件：`app/observability/metrics.py`、日志配置、`deploy/prometheus.yml`。
- 编码：暴露受部署网络保护的 `/metrics`；记录接口耗时、错误率、额度拒绝、重复事件数、Outbox 积压及账单任务失败数。
- 编码：日志关联 request_id/event_id/period_id；指标标签不用 tenant_id、event_id 等高基数字段；告警条件写入 `docs/operations.md`。
- 验收：制造一次额度不足和 Worker 停止，能从指标识别；由 request_id 找到对应日志；日志无敏感凭据。

### 第 27 天｜关键链路测试与 CI

**目标：**把已有验证固化为提交时必跑的检查。

- 文件：`tests/conftest.py`、`tests/integration/test_billing_flow.py`、`.github/workflows/ci.yml`。
- 编码：创建隔离测试数据库/数据清理策略；覆盖完整业务闭环和前面累计的隔离、并发、回调、重试测试；CI 启动 PostgreSQL、Redis 后迁移并运行测试。
- 编码：Ruff 与关键类型检查进入 CI；测试不依赖真实支付和外部网络；失败保留相关日志。
- 验收：全新环境能运行全部关键测试；通过破坏一个幂等条件确认测试确实会失败，再恢复代码。

### 第 28 天｜压测、查询分析与一次优化

**目标：**给出有环境说明的性能证据。

- 文件：`scripts/load_usage.py`、`scripts/seed_benchmark.py`、`docs/benchmark.md`。
- 编码：准备至少 10 万条事件，分别测新事件、幂等重放、用量查询；报告并发数、硬件、数据量、成功率、p50/p95 及数据库连接数。
- 分析：对慢查询做 EXPLAIN ANALYZE；只依据证据增加索引或调整分页/聚合；记录优化前后同条件数据。
- 验收：压测后无超额扣减和重复事件；尽量达成测试环境 p95 < 300ms 的本地目标，未达成时记录原因和实测值，不编造高并发结论。

### 第 29 天｜容器部署与最小管理页面

**目标：**他人能启动项目并看见业务结果。

- 文件：`deploy/Dockerfile`、`deploy/compose.yml`、`app/templates/dashboard.html`、`app/modules/demo/dashboard.py`。
- 编码：提供 API、Worker、Outbox、数据库、Redis 启动配置与健康检查；迁移用单独命令执行；页面只展示订阅、额度、账单和审计，复用现有鉴权接口。
- 编码：保留非 root 运行、只读配置及数据卷；页面不把密钥放 URL，也不绕过租户查询。公网 HTTPS 和基础设施配置写作部署要求，不直接发布。
- 验收：从空数据库按 README 启动并完成演示；重启服务后数据保留；无手工改数据库的隐藏步骤。

### 第 30 天｜交付、演示与技术说明

**目标：**形成可以展示、复现和讲解的项目版本。

- 文件：`README.md`、`docs/{architecture,decisions,demo,limitations}.md`、`scripts/demo_flow.py`。
- 编码：演示脚本准备两个企业并跑通全链路；演示租户越权拒绝、并发额度上限、重复回调三类关键行为。
- 整理：记录事务边界、价格快照、Outbox 语义和计费归属规则；补齐安装步骤、测试命令、架构图、真实压测数据与参考来源，打版本标签。
- 验收：另一人能仅依赖 README 启动；所有关键检查通过；限制项清楚；可用 10 分钟讲完整业务与 3 个技术难点。

## 7. 关键代码契约草图

这些是实现方向，不是可直接粘贴的完整代码。

```python
async def consume_usage(
    session: AsyncSession,
    tenant: TenantContext,
    command: UsageIn,
) -> UsageResult:
    # 调用方持有一个完整业务事务；这里不自行提前 commit。
    # 1. 校验租户与 scope；已完成事件核对摘要并返回原快照或 409。
    # 2. 获取/锁定订阅和开放周期；必要时完成到期轮转。
    # 3. 尝试插入事件；并发重复仍由唯一约束裁决并读取原结果。
    # 4. 对 quota 进行带上限条件的原子 UPDATE。
    # 5. 失败则回滚整笔事务；成功由调用方提交。
    ...


def calculate_invoice(snapshot: PricingSnapshot, quantity: int) -> InvoiceDraft:
    # base_fee_cents + quantity * unit_price_cents
    # 只处理整数，不访问数据库，不调用外部服务。
    ...
```

幂等异常处理可以选择 `INSERT ... ON CONFLICT` 或 savepoint；实际方案以事务测试为准。捕获 IntegrityError 后不能继续使用已经失败的事务。

## 8. 阶段交付与最终验收清单

| 时间点 | 必须能演示的成果 |
|---|---|
| 第 07 天 | 注册、登录、企业成员权限、API Key 创建与撤销 |
| 第 14 天 | 套餐订阅、服务端计量、幂等重放、并发额度控制 |
| 第 20 天 | 用量查询、审计、可靠任务、周期关闭与续期 |
| 第 25 天 | 账单、模拟付款、重复/乱序回调、对账报告 |
| 第 30 天 | CI、性能报告、容器部署、完整演示及技术文档 |

- [ ] 两个租户的成员、密钥、用量、账单均无法互相读取或修改。
- [ ] 幂等重放不重复计量，冲突内容返回明确错误。
- [ ] 并发测试不超出硬额度，失败业务不消耗额度。
- [ ] 账单能从周期条款与用量事件复算；价格修改不改变历史费用。
- [ ] Worker 重启或消息重复投递不重复生成账单。
- [ ] 非法签名、金额不符、重复和乱序回调不导致错误付款状态。
- [ ] 启动文档、CI 与实测性能报告完整。
- [ ] 演示使用模拟支付，项目未宣称已上线真实收款或达到某个生产规模。

## 9. 完成主线后再考虑的扩展

按需要选择一项深入：PostgreSQL RLS、多计量维度、真实支付测试环境、预留/确认额度协议、开放 Webhook 的可靠投递、超额计费或财务调整单。每项重新估时，不塞进已经安排好的 30 天。

求职描述应强调独立完成的模块和真实测试证据。例如：“设计租户级幂等事件与数据库条件扣减，在 200 并发请求、100 次硬额度的测试中验证只接受 100 次消费。”使用时必须替换为自己实际完成的数据。

## 10. 参考资料

- [Polar 开源仓库](https://github.com/polarsource/polar)：参考真实商业业务划分。
- [Polar 开发说明](https://github.com/polarsource/polar/blob/main/DEVELOPMENT.md)：参考开发环境与工程协作。
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)：应用资源的初始化与关闭。
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)：异步 Session 的生命周期及并发边界。

## 11. 每天的进度记录模板

```markdown
### 第 XX 天｜实际日期：
- 今日目标：
- 已完成文件/函数/接口：
- 验证命令与结果：
- 遇到的问题及取舍：
- 未完成项及下一步：
- Git commit：
```

执行原则：当天可运行、可验证、可提交后再进入下一天。前置验收失败时先修复依赖，不用“已完成目录创建”代替业务能力完成。
