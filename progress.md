# MeterGate｜进度与交接

> 最后更新：2026-10-15（Asia/Shanghai）。开发完成 2 / 30；第 02 天验收通过。
> 本文件是本仓库唯一的进度记录；计划见 [docs/plan.md](docs/plan.md)。

## 接续规则

1. 开发前读取本文件、对应日计划和实际代码，从下一步继续，不重新初始化已有实现。
2. 部分完成时写清剩余子任务；通过验收后才推进任务编号。
3. 开发结束后更新当前状态、修改文件、验证结果、问题和下一步；未执行的检查写未执行。
4. 路径相对于本仓库；密钥、.env、.venv、运行数据不进 Git。
5. 本项目已有独立 .git、.gitignore、.gitattributes、依赖锁文件和计划，可以单独 clone 和运行。
6. Python 文件开头维护一句中文 `# 用途：` 注释；新增或调整代码职责时，同步更新 [代码用途汇总](docs/code-map.md)，预留功能必须注明尚未实现。
7. 用户可见状态、错误提示与接口说明统一使用中文；接口字段名、URL、HTTP 状态码、项目名和版本号保持原样。后续接口延续此约定。

## 仓库状态

- 本地根目录：当前 metergate 文件夹。初始化分支为 codex/initial。
- 2026-10-12 从原共享工作目录拆分；原父仓库的暂存区与配置备份在父目录 .local/repository-backups，不是本项目依赖。
- origin：https://github.com/zmq2783764729-crypto/MeterGate.git。提交身份使用用户选择的 GitHub 用户名与隐私邮箱；同步状态按 git status 与远端检查核实。
- GitHub 已推送：本机 codex/initial 跟踪 origin/main，远端已有 main 历史已合并保留；本机 push.default=upstream，因此日常直接 git push 即可。其他电脑 clone 后按实际默认分支使用。
- 当前电脑 Git 网络配置：本仓库本地 http.proxy 使用系统已启用的 `http://127.0.0.1:7897`；只保存在本机 .git/config，不随 clone 传播。代理端口变更时按本机实际配置调整。
- Python 3.12；按 README 用 uv sync --locked 重建环境。本机辅助 uv 在父目录 .local/bootstrap/bin，不随仓库同步。
- 本机辅助 uv 尚未加入 PATH，当前电脑启动方法见 README；其他电脑需先安装 Python 3.12 与 uv。
- Docker Desktop 与开发容器已运行：2026-10-14 用户完成 PostgreSQL/Redis 启动练习，助手复核两项 healthy、SELECT 1 与 PONG 通过。

## MeterGate｜企业服务计量与结算平台

### 项目约定

- 计划：[MeterGate 30 天计划](docs/plan.md)。
- 代码目录：本仓库根目录；启动说明见 [README](README.md)。
- 核心业务：企业与成员、API Key、套餐订阅、用量额度、账单、模拟支付和审计。
- 技术路线：FastAPI、Pydantic、PostgreSQL、SQLAlchemy、Alembic、Redis、Dramatiq；模块化单体。
- 首版限制：CNY 单币种、整数分金额、每月计费、套餐下周期变更、模拟支付。
- 关键设计：租户级幂等键、数据库条件扣减、周期价格快照、事务 Outbox；细节按原计划。

### 当前进度

- 已完成：第 01、02 天；应用骨架、数据库/Redis 连接与生命周期、独立会话、首次 Alembic 迁移、live/ready 与故障恢复验收。
- 当前任务：第 02 天验收通过，等待开始第 03 天。完整证据见 [验收记录](docs/day02-acceptance.md)。
- 关键文件：`pyproject.toml`、`uv.lock`、`.python-version`、`.env.example`、`app/main.py`、`app/core/config.py`、`app/api/{router,health}.py`、`tests/test_app.py`、`docs/scope.md`、`README.md`。
- 已实现：`Settings`、`create_app()`、连接资源 `lifespan()`、`GET /health/live` 与 `/health/ready`；Base、async_sessionmaker、get_session。配置用 MG_ 前缀，连接地址/密钥使用 SecretStr；service 显式决定事务提交，Session 不自动提交。
- 最新完整测试：`.venv/Scripts/python.exe -m pytest -p no:cacheprovider` 为 **11 passed**，包含当前中文响应预期；锁文件一致性、全项目 Ruff 检查与格式检查通过。
- 最新真实连接验证：独立 Session、SELECT 1、会话退出回滚未提交事务、归还连接、lifespan 关闭 PostgreSQL/Redis 连接通过；使用独立测试库，未修改用户 .env 或开发库。
- 实际故障验证：用户停止 PostgreSQL，live=200、ready=503；恢复后无需重启应用，ready=200。截图证据通过，助手最后读取当前 8000 端口 live/ready 均为 200。
- 迁移：alembic.ini、migrations/env.py、版本文件模板已配置；0001_baseline 执行成功，数据库 alembic_version.version_num 为 0001_baseline。此版本 upgrade/downgrade 为空操作，仅建立迁移基线，不代表业务表已创建。
- 空库迁移：专属测试库从 0 张 public 表升级到 0001_baseline，重复 upgrade head 成功；资源关闭后测试库连接数为 0，测试库已删除。
- 问题/待定项：第 02 天无剩余验收项；业务模型尚未实现。当前中文错误处理已有 HTTP/参数/内部错误响应，第 03 天应在此基础上继续，不能覆盖用户已有中文约定。

### 下一步：第 03 天

1. 读取计划第 03 天，保留现有连接层、0001_baseline 和中文错误处理，按用户动手、助手讲解与核验的方式推进。
2. 定义 DomainError，统一 code/message/request_id 错误结构；保留正确的 HTTP 状态码与响应头。
3. 实现请求标识中间件与结构化日志，将 request_id 写入响应头和日志，日志不包含密码、JWT 或 API Key。
4. 验证无效参数、缺少认证、未知错误与请求追踪；完成后更新本文件，不提前计入第 03 天。

## 最近记录

### 2026-10-15｜第 02 天最终验收通过

- 用户完成真实停库/恢复练习：live=200、数据库不可用时 ready=503、恢复后 ready=200，Redis 始终正常。
- 助手收尾：当前完整测试 11 passed；锁文件一致性、全项目 Ruff 检查和格式检查通过。
- 独立空数据库：迁移前 0 张 public 表，升级后版本为 0001_baseline，仅有版本表；重复升级成功。验证真实会话独立、退出时回滚未提交临时表，以及 PostgreSQL/Redis 连接关闭。
- 清理：临时库 metergate_day02_acceptance_0715b7c95022 已删除；未修改用户 .env、未改写开发库、未再次停止用户服务或容器。
- 结论：第 02 天通过，开发完成更新为 2 / 30；验收说明见 docs/day02-acceptance.md。下一步第 03 天，尚未开始实现。
- 同步：更改仍在本地，未提交或推送；用户已有 .idea/ 保持原样。

### 2026-10-15｜用户完成首次 Alembic 迁移

- 用户操作：开发容器 healthy，生成 0001_baseline，并执行 upgrade head 成功；截图可见 Running upgrade -> 0001_baseline。
- 助手复核：alembic current 输出 0001_baseline (head)；直接查询数据库版本表同样返回 0001_baseline。
- 配置：迁移读取 Settings 与 Base.metadata，使用异步 PostgreSQL 连接与 NullPool，finally 释放连接；新版本文件自动带用途注释并由 Ruff 格式化。
- 边界：首次迁移只建立版本基线，不创建业务表；尚未认定第 02 天全部完成。
- 下一步：用户实际停止 PostgreSQL，验证 ready=503/live=200，恢复后 ready=200；之后执行最终检查。
- 本次未停止用户容器，未重复执行迁移，未提交或推送。

### 2026-10-14｜用户可见返回改为中文

- 范围：按用户要求，仅修改当前 MeterGate 的返回文本与接口说明，保留 JSON 字段名、URL、HTTP 状态码、项目名和版本号。
- 健康返回：live 的 status 改为正常；ready 改为已就绪/未就绪；检查项改为正常/不可用/未配置。旧脚本若比较 ok/ready/not_ready/unavailable/not_configured，需要调整为对应中文值。
- 错误：数据库未配置提示改为中文；新增 core/errors.py 注册中文 HTTP 错误、参数校验与内部错误响应。保留 HTTP 错误状态码和响应头，不返回原始内部异常或校验输入。
- 文档与测试：同步第 02 天示例、README、用途汇总和已有测试预期。新增中文化测试 3 passed，Ruff 检查/格式检查通过；完整异步测试和真实 HTTP 未在本次执行。
- 本次没有推进数据库迁移或调整主任务的下一步；开发完成仍为 1 / 30。未修改 .env、未操作容器、未提交或推送。

### 2026-10-14｜练习 1 通过，实现练习 2 连接层

- 用户反馈全部环境验证通过；助手复核两个容器 healthy、SELECT 1、PONG。
- 依赖：安装并锁定 SQLAlchemy 2.0.54、asyncpg 0.32.0、Alembic 1.20.0、redis-py 8.1.0。
- 文件：新增 app/db/base.py、app/db/session.py、tests/test_db_runtime.py；更新 main.py、config.py、health.py、.env.example、代码用途汇总和操作文档。
- 实现：应用级连接池、请求独立 Session、service 负责提交；AsyncExitStack 释放正常/异常路径的资源；ready 并行探测 PostgreSQL 与 Redis，超时或失败返回 503，响应隐藏凭据。
- 验证：8 项测试通过；真实数据库与 Redis 连接、事务回滚、资源关闭、HTTP ready=200/live=200；连接拒绝时 ready=503/live=200。未修改用户 .env，也未停止用户容器；已停止本次 HTTP 验收进程与因沙箱限制卡住的本次测试进程。
- 静态检查：锁文件一致性检查、全项目 Ruff 检查与格式检查、git diff --check 通过。
- 用户下一步：完成 .env 配置和应用启动练习，反馈 ready 输出；之后讲解并配置 Alembic，执行空库迁移及实际停库验收。
- 第 02 天尚未全部完成，开发完成仍为 1 / 30；更改尚未提交或推送。

### 2026-10-13｜开始第 02 天：练习 1

- 用户要求：一边讲解一边实施，保留用户实际操作与学习的机会。
- 环境检查：Docker CLI 与 Compose 可用，但 Docker API 连接失败，未检测到 Docker 相关运行进程；不能认定数据库已启动。WSL 状态命令在当前执行环境返回 E_ACCESSDENIED，不能据此判断用户终端中的 WSL 状态。
- 文件：新增 deploy/compose.dev.yml 与 docs/day02-practice.md。Compose 提供 PostgreSQL、Redis、回环端口绑定、健康检查与数据卷。
- 已验证：docker compose -f deploy/compose.dev.yml config --quiet 与 git diff --check 通过；尚未拉取镜像、启动容器或执行数据库验证。
- 下一步：用户打开 Docker Desktop，确认 docker version 包含 Server，按练习启动数据服务并反馈 ps/SELECT 1/PONG；随后继续 Python 连接与迁移。
- 未完成：Python 数据访问依赖与锁文件更新、Base/会话依赖、连接资源生命周期、Alembic 迁移、ready 接口、数据库故障验收。
- 开发完成仍为 1 / 30；本次更改尚未提交或推送。

### 2026-10-12｜第 01 天逐项复验

- 发现并修正：范围文档缺少详细计费规则；计划内 Python 示例缺少空行，完整格式检查失败。补齐 docs/scope.md，修正 docs/plan.md，README 加入本机可用启动命令。
- 验证：全新虚拟环境按锁文件离线安装成功；锁文件一致性、全项目 Ruff 检查与格式检查通过；pytest 为 **1 passed**；真实 HTTP 健康、OpenAPI、文档页面通过。
- 补充核验：配置文件读取、环境变量优先级、非法配置拒绝、测试密钥显示脱敏、生命周期异常退出、Git 凭据排除规则通过。验收细节见 docs/day01-acceptance.md。
- 结论：第 01 天通过，开发完成仍为 1 / 30；本次没有实施第 02 天功能。
- 同步：本次复验与此前代码用途说明仍在本地，尚未提交或推送；用户已有 .idea/ 保持原样。

### 2026-10-12｜代码阅读说明

- 完成：为本仓库全部 26 个 Python 文件添加一条文件用途注释，包括应用代码、测试和预留包入口；新增 docs/code-map.md 汇总，README 增加阅读入口。
- 验证：添加注释前后逐文件比较 AST，26 个文件均一致；Python 代码 Ruff 检查和格式检查通过；汇总条目与首行注释逐一核对。
- 范围：本次仅处理 MeterGate，没有修改 BriefPilot；没有实现新业务，开发进度仍为 1 / 30，继续第 02 天。
- 同步：本次说明修改保留在本地工作区，尚未创建提交或推送；用户已有 .idea/ 文件保持原样。

### 2026-10-12｜拆为独立仓库

- 完成：本项目单独的计划、进度、Git 忽略/换行规则；README 和范围文档链接改为仓库内路径。
- 代码：保留第 01 天全部实现与依赖锁文件，未改动业务代码。
- 验证：第 01 天测试结果沿用上文已有记录；此次仅检查拆分后的 Git 边界、文件链接和排除规则，不声称重新执行应用测试。
- 提交/同步：初始代码提交 257d44c，合并提交 dea1458；正常推送到 origin/main，保留 GitHub 原始 c1eadc1 提交与 README 描述，没有强制推送。交接文档随后单独提交同步。
- 下一步：应用开发继续第 02 天；在本仓库使用 git pull --ff-only、git push，同步代码与 progress.md。

## 开工提示词

```text
请读取本仓库 progress.md 与 docs/plan.md，核对现有代码，从下一步继续；结束后更新同一个 progress.md，记录完成项、实际验证结果、问题和下一步。
```
