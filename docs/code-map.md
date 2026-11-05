# MeterGate代码文件用途汇总

> 更新时间：2026-11-04。与每个Python文件首行用途注释对应。

当前共 **96 个Python文件**。预留模块不代表已经实现。

## 已有实现与包入口

| 文件 | 文件首行用途说明 |
|---|---|
| [app/__init__.py](../app/__init__.py) | 标识 MeterGate 应用包并提供应用版本号。 |
| [app/api/__init__.py](../app/api/__init__.py) | 标识HTTP接口辅助包，提供健康检查处理及独立应用的路由复制。 |
| [app/api/health.py](../app/api/health.py) | 提供 live 存活检查和 PostgreSQL/Redis 的 ready 就绪检查，故障时返回 503 且隐藏凭据。 |
| [app/api/router.py](../app/api/router.py) | 为独立应用工厂复制已声明的 HTTP 接口，保持依赖覆盖与应用配置隔离。 |
| [app/core/__init__.py](../app/core/__init__.py) | 标识核心配置包，当前包含环境配置模块。 |
| [app/core/config.py](../app/core/config.py) | 读取 MG_ 环境变量和本项目 .env，校验配置并隐藏数据库地址与密钥的显示值。 |
| [app/core/errors.py](../app/core/errors.py) | 定义领域错误并统一中文错误响应，关联请求编号且隐藏原始异常和敏感输入。 |
| [app/core/logging.py](../app/core/logging.py) | 配置安全的 JSON 日志，仅输出允许的请求元数据并阻止访问日志和异常文本泄露敏感值。 |
| [app/core/security.py](../app/core/security.py) | 使用 Argon2 哈希验证密码，并按固定算法、签发方、接收方和期限签发校验访问令牌。 |
| [app/db/__init__.py](../app/db/__init__.py) | 标识数据库包，提供模型基类、异步连接池和请求会话管理。 |
| [app/db/base.py](../app/db/base.py) | 提供 SQLAlchemy 模型基类，供后续业务模型与 Alembic 共享表结构元数据。 |
| [app/db/session.py](../app/db/session.py) | 创建 PostgreSQL 异步连接池和会话工厂，为每次请求提供独立会话且不自动提交事务。 |
| [app/dependencies/__init__.py](../app/dependencies/__init__.py) | 标识依赖注入包，提供用户与机器认证、租户成员身份、角色和scope校验。 |
| [app/dependencies/api_key.py](../app/dependencies/api_key.py) | 验证X-API-Key摘要、撤销和有效期，并通过可复用依赖限定机器调用scope。 |
| [app/dependencies/auth.py](../app/dependencies/auth.py) | 注入认证配置，验证 Bearer 访问令牌，并从数据库加载当前登录用户。 |
| [app/dependencies/permissions.py](../app/dependencies/permissions.py) | 提供可复用角色依赖，在可信租户上下文基础上限制接口允许的成员角色。 |
| [app/dependencies/tenant.py](../app/dependencies/tenant.py) | 将URL企业编号与已认证用户的数据库成员关系匹配，生成可信租户上下文。 |
| [app/main.py](../app/main.py) | 在模块顶层使用 @app 定义接口，并配置应用工厂、错误处理、日志及数据库和 Redis 生命周期。 |
| [app/middleware/__init__.py](../app/middleware/__init__.py) | 标识请求上下文中间件包，提供请求编号管理。 |
| [app/middleware/request_context.py](../app/middleware/request_context.py) | 管理每次请求的独立编号与响应头，输出安全的完成或失败日志，并清理上下文。 |
| [app/modules/__init__.py](../app/modules/__init__.py) | 标识业务模块包，为企业、订阅、计量和结算功能预留分层目录。 |
| [app/modules/api_keys/__init__.py](../app/modules/api_keys/__init__.py) | 标识企业API Key业务包，提供创建、列表、撤销和机器身份scope校验。 |
| [app/modules/api_keys/context.py](../app/modules/api_keys/context.py) | 提供通过API Key验证的机器身份，租户和权限仅来自数据库密钥记录。 |
| [app/modules/api_keys/models.py](../app/modules/api_keys/models.py) | 定义企业API Key表，仅保存令牌摘要、显示前缀、权限范围、有效期及撤销状态。 |
| [app/modules/api_keys/repository.py](../app/modules/api_keys/repository.py) | 按可信租户上下文写入、分页和查找密钥，机器认证仅按公开编号定位摘要记录。 |
| [app/modules/api_keys/router.py](../app/modules/api_keys/router.py) | 为main.py提供API Key管理处理函数及两种scope的机器身份校验依赖。 |
| [app/modules/api_keys/schemas.py](../app/modules/api_keys/schemas.py) | 校验密钥名称、权限和有效期，分开定义一次性完整密钥响应与普通公开元数据。 |
| [app/modules/api_keys/security.py](../app/modules/api_keys/security.py) | 生成256位随机API Key并计算SHA-256摘要，解析格式且隐藏内存对象中的敏感值。 |
| [app/modules/api_keys/service.py](../app/modules/api_keys/service.py) | 在管理员授权事务内创建或撤销企业密钥，列表只输出安全元数据。 |
| [app/modules/auth/__init__.py](../app/modules/auth/__init__.py) | 标识用户认证业务包，包含用户模型、注册登录分层实现与公开响应结构。 |
| [app/modules/auth/models.py](../app/modules/auth/models.py) | 定义用户表，保存唯一邮箱、密码哈希、UUID 主键和带时区的创建时间。 |
| [app/modules/auth/repository.py](../app/modules/auth/repository.py) | 通过异步会话查询和添加用户，写入时 flush 但不自行提交事务。 |
| [app/modules/auth/router.py](../app/modules/auth/router.py) | 提供 main.py 顶层认证接口调用的处理函数，以及会话和配置依赖类型。 |
| [app/modules/auth/schemas.py](../app/modules/auth/schemas.py) | 校验注册登录输入、统一邮箱大小写，并定义不含密码哈希的用户与令牌响应。 |
| [app/modules/auth/service.py](../app/modules/auth/service.py) | 编排用户注册和密码认证，管理注册事务并将邮箱唯一冲突转换为业务错误。 |
| [app/modules/catalog/__init__.py](../app/modules/catalog/__init__.py) | 标识平台套餐业务包，提供只追加价格版本、演示初始化和公开只读查询。 |
| [app/modules/catalog/models.py](../app/modules/catalog/models.py) | 定义稳定套餐与只追加价格版本，约束币种、计费周期、金额、额度和版本唯一性。 |
| [app/modules/catalog/repository.py](../app/modules/catalog/repository.py) | 查询公开套餐及历史版本，锁定套餐分配版本号，写入价格版本但不提交事务。 |
| [app/modules/catalog/router.py](../app/modules/catalog/router.py) | 为main.py公开套餐只读接口提供会话依赖和处理函数，不提供租户管理员发布接口。 |
| [app/modules/catalog/schemas.py](../app/modules/catalog/schemas.py) | 严格校验整数分金额和正整数额度，并定义套餐、历史版本与分页公开响应。 |
| [app/modules/catalog/service.py](../app/modules/catalog/service.py) | 以追加方式发布价格版本，幂等初始化演示套餐，并组装公开套餐与历史版本查询。 |
| [app/modules/subscriptions/__init__.py](../app/modules/subscriptions/__init__.py) | 标识订阅业务包，已实现开通、快照、预约与到期取消，完整周期轮转后续实现。 |
| [app/modules/subscriptions/models.py](../app/modules/subscriptions/models.py) | 定义订阅、周期和不可变条款快照，约束套餐预约与到期取消字段及租户归属。 |
| [app/modules/subscriptions/periods.py](../app/modules/subscriptions/periods.py) | 提供UTC时钟、保留账单日锚点的日历月边界，以及左闭右开周期归属判断。 |
| [app/modules/subscriptions/repository.py](../app/modules/subscriptions/repository.py) | 按可信租户查询、锁定和写入订阅周期及条款，数据写入仅flush而不提交。 |
| [app/modules/subscriptions/router.py](../app/modules/subscriptions/router.py) | 为main.py提供订阅开通、预约、取消和读取处理，复用可信租户与管理员依赖。 |
| [app/modules/subscriptions/schemas.py](../app/modules/subscriptions/schemas.py) | 限定订阅开通与预约请求字段，定义含周期快照、预约取消和消费前置状态的响应。 |
| [app/modules/subscriptions/service.py](../app/modules/subscriptions/service.py) | 事务化开通、预约套餐与到期取消，读取时结算到期取消，并提供消费前置校验。 |
| [app/modules/subscriptions/transitions.py](../app/modules/subscriptions/transitions.py) | 集中定义订阅允许的预约动作和消费时间判断，阻止取消后复活及跨周期消费。 |
| [app/modules/tenants/__init__.py](../app/modules/tenants/__init__.py) | 标识企业业务包，提供企业创建、租户上下文、成员管理和管理员保护。 |
| [app/modules/tenants/authorization.py](../app/modules/tenants/authorization.py) | 为企业管理写事务锁定企业行，并复核操作者当前数据库中的管理员身份。 |
| [app/modules/tenants/context.py](../app/modules/tenants/context.py) | 提供不可变租户上下文，携带经过数据库成员关系验证的企业、用户和角色。 |
| [app/modules/tenants/models.py](../app/modules/tenants/models.py) | 定义企业和成员关系表，通过外键、角色检查与联合唯一约束保护成员数据。 |
| [app/modules/tenants/repository.py](../app/modules/tenants/repository.py) | 按用户或可信租户上下文访问企业成员数据，并提供管理操作的企业行锁与管理员计数。 |
| [app/modules/tenants/router.py](../app/modules/tenants/router.py) | 为main.py企业与成员接口提供处理函数、租户和角色依赖以及独立业务会话。 |
| [app/modules/tenants/schemas.py](../app/modules/tenants/schemas.py) | 校验企业和成员请求，定义企业、成员及items/next_cursor分页的公开响应。 |
| [app/modules/tenants/service.py](../app/modules/tenants/service.py) | 编排企业与成员管理事务，复核管理员权限并通过企业行锁保护最后一位管理员。 |
| [migrations/env.py](../migrations/env.py) | 读取应用配置与模型元数据，通过异步 PostgreSQL 连接执行 Alembic 迁移或输出 SQL。 |
| [migrations/versions/0001_baseline_initialize_migration_baseline.py](../migrations/versions/0001_baseline_initialize_migration_baseline.py) | initialize migration baseline；记录本次表结构升级与回退操作。 |
| [migrations/versions/0002_users_create_users_table.py](../migrations/versions/0002_users_create_users_table.py) | 创建 users 表与邮箱唯一约束，回退时删除用户表。 |
| [migrations/versions/0003_tenants_create_tenants_and_memberships.py](../migrations/versions/0003_tenants_create_tenants_and_memberships.py) | 创建企业及成员关系表、外键、角色检查和联合唯一约束，回退时按依赖逆序删除。 |
| [migrations/versions/0004_api_keys_create_api_keys.py](../migrations/versions/0004_api_keys_create_api_keys.py) | 创建只保存摘要的企业API Key表，包含权限与有效期约束，回退时删除密钥表。 |
| [migrations/versions/0005_catalog_create_plans_and_immutable_versions.py](../migrations/versions/0005_catalog_create_plans_and_immutable_versions.py) | 创建套餐和价格版本表，并以数据库触发器禁止修改、删除或清空历史版本。 |
| [migrations/versions/0006_subscriptions_create_subscriptions_periods_and_terms.py](../migrations/versions/0006_subscriptions_create_subscriptions_periods_and_terms.py) | 创建企业订阅、计费周期和不可变条款快照，保护企业唯一订阅与单个开放周期。 |
| [migrations/versions/0007_subscription_actions_add_scheduled_subscription_actions.py](../migrations/versions/0007_subscription_actions_add_scheduled_subscription_actions.py) | 增加订阅预约与到期取消字段，并约束预约字段完整性和取消优先规则。 |
| [scripts/__init__.py](../scripts/__init__.py) | 标识本机平台维护脚本包，脚本通过项目解释器运行，不作为HTTP接口开放。 |
| [scripts/seed_catalog.py](../scripts/seed_catalog.py) | 幂等初始化基础与专业套餐，或通过平台本机命令追加新价格版本，拒绝非法金额和额度。 |
| [tests/test_api_key_contract.py](../tests/test_api_key_contract.py) | 验证API Key生成解析、输入边界与畸形密钥在查库前得到401。 |
| [tests/test_api_key_database.py](../tests/test_api_key_database.py) | 在专属PostgreSQL库验证密钥摘要存储、管理员隔离、scope、过期、撤销和日志安全。 |
| [tests/test_app.py](../tests/test_app.py) | 验证应用配置互不串用、健康响应与配置显示不泄露测试密钥，以及生命周期正常结束。 |
| [tests/test_auth_database.py](../tests/test_auth_database.py) | 在专属 PostgreSQL 测试库验证注册登录、真实唯一约束并发冲突、令牌身份和敏感值隐藏。 |
| [tests/test_auth_security.py](../tests/test_auth_security.py) | 验证 Argon2 密码、邮箱输入和 JWT 的签名、声明、算法白名单与认证配置边界。 |
| [tests/test_catalog_contract.py](../tests/test_catalog_contract.py) | 验证价格和额度的严格整数边界，拒绝负数、浮点、布尔值及非法计费条款。 |
| [tests/test_catalog_database.py](../tests/test_catalog_database.py) | 在专属PostgreSQL库验证套餐幂等初始化、追加版本、并发编号、历史不可改和公开查询。 |
| [tests/test_db_runtime.py](../tests/test_db_runtime.py) | 验证就绪检查的故障、超时与脱敏行为，以及连接资源在正常和异常路径下正确释放。 |
| [tests/test_error_contract.py](../tests/test_error_contract.py) | 验证领域、HTTP、参数和未知错误的统一响应、请求编号一致性及敏感内容隐藏。 |
| [tests/test_member_contract.py](../tests/test_member_contract.py) | 验证成员输入边界与四个成员接口的未认证401响应，避免暴露租户数据。 |
| [tests/test_member_database.py](../tests/test_member_database.py) | 在专属PostgreSQL库验证跨租户授权、角色即时生效及并发修改下最后管理员保护。 |
| [tests/test_request_context.py](../tests/test_request_context.py) | 验证请求编号在成功与错误响应中一致可查、每请求唯一、并发隔离且异常后正确清理。 |
| [tests/test_request_logging.py](../tests/test_request_logging.py) | 验证请求与错误日志的编号关联、并发隔离、字段安全、日志级别及重复配置行为。 |
| [tests/test_response_language.py](../tests/test_response_language.py) | 验证中文健康状态、接口说明和错误提示，并确保参数与内部异常不泄露到响应。 |
| [tests/test_subscription_actions_database.py](../tests/test_subscription_actions_database.py) | 在专属数据库验证订阅预约、到期取消、消费阻止、幂等与并发状态迁移。 |
| [tests/test_subscription_contract.py](../tests/test_subscription_contract.py) | 验证UTC日历月、闰年月末和左闭右开边界，以及开通请求禁止伪造时间与价格。 |
| [tests/test_subscription_database.py](../tests/test_subscription_database.py) | 在专属PostgreSQL库验证订阅原子开通、并发去重、快照不变、月末及跨租户授权。 |
| [tests/test_tenant_contract.py](../tests/test_tenant_contract.py) | 验证企业名称与额外字段校验，以及企业接口在缺少有效身份时返回统一401错误。 |
| [tests/test_tenant_database.py](../tests/test_tenant_database.py) | 在专属PostgreSQL库验证企业管理员创建、用户隔离、游标分页、失败回滚及真实成员约束。 |
| [tests/unit/test_subscription_transitions.py](../tests/unit/test_subscription_transitions.py) | 验证订阅预约状态迁移与消费边界，覆盖取消标记、已取消和周期结束时刻。 |

## 尚未实现的预留模块

| 文件 | 文件首行用途说明 |
|---|---|
| [app/integrations/__init__.py](../app/integrations/__init__.py) | 预留支付等外部服务的适配器包，尚未实现。 |
| [app/integrations/payments/__init__.py](../app/integrations/payments/__init__.py) | 预留支付提供方接口及模拟支付适配器包，尚未实现。 |
| [app/modules/audit/__init__.py](../app/modules/audit/__init__.py) | 预留关键业务操作的审计记录和审计查询模块，尚未实现。 |
| [app/modules/billing/__init__.py](../app/modules/billing/__init__.py) | 预留周期计价、账单生成、账单查询和对账业务模块，尚未实现。 |
| [app/modules/demo/__init__.py](../app/modules/demo/__init__.py) | 预留服务端计量的数据查询演示接口及结果重放业务模块，尚未实现。 |
| [app/modules/metering/__init__.py](../app/modules/metering/__init__.py) | 预留用量事件、幂等接收、并发额度扣减和用量查询业务模块，尚未实现。 |
| [app/modules/payments/__init__.py](../app/modules/payments/__init__.py) | 预留支付会话、回调验签、回调幂等和账单付款状态业务模块，尚未实现。 |
| [app/observability/__init__.py](../app/observability/__init__.py) | 预留运行指标及其他可观测性功能包，尚未实现。 |
| [app/workers/__init__.py](../app/workers/__init__.py) | 预留后台任务、消息代理和事务 Outbox 执行包，尚未实现。 |

## 第10天阅读路线

1. app/main.py两个操作接口 → subscriptions/router.py依赖 → service.py事务。
2. subscriptions/models.py与schemas.py：六个持久化字段、动态can_consume和请求约束。
3. subscriptions/transitions.py与repository.py：状态时间规则及租户行锁。
4. 0007_subscription_actions迁移、tests/unit/test_subscription_transitions.py及test_subscription_actions_database.py。
5. [详细学习文档](day10-practice.md)、[状态转换表](subscription_states.md)与[逐行实测记录](day10-test-cases.md)。

唯一进度记录为[progress.md](../progress.md)，本文件只汇总代码职责。
