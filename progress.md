# MeterGate｜进度与交接

> 最后更新：2026-10-12（Asia/Shanghai）。开发完成 1 / 30。
> 本文件是本仓库唯一的进度记录；计划见 [docs/plan.md](docs/plan.md)。

## 接续规则

1. 开发前读取本文件、对应日计划和实际代码，从下一步继续，不重新初始化已有实现。
2. 部分完成时写清剩余子任务；通过验收后才推进任务编号。
3. 开发结束后更新当前状态、修改文件、验证结果、问题和下一步；未执行的检查写未执行。
4. 路径相对于本仓库；密钥、.env、.venv、运行数据不进 Git。
5. 本项目已有独立 .git、.gitignore、.gitattributes、依赖锁文件和计划，可以单独 clone 和运行。

## 仓库状态

- 本地根目录：当前 metergate 文件夹。初始化分支为 codex/initial。
- 2026-10-12 从原共享工作目录拆分；原父仓库的暂存区与配置备份在父目录 .local/repository-backups，不是本项目依赖。
- origin：https://github.com/zmq2783764729-crypto/MeterGate.git。提交身份使用用户选择的 GitHub 用户名与隐私邮箱；同步状态按 git status 与远端检查核实。
- GitHub 已推送：本机 codex/initial 跟踪 origin/main，远端已有 main 历史已合并保留；本机 push.default=upstream，因此日常直接 git push 即可。其他电脑 clone 后按实际默认分支使用。
- Python 3.12；按 README 用 uv sync --locked 重建环境。本机辅助 uv 在父目录 .local/bootstrap/bin，不随仓库同步。
- Docker 的 Virtual Machine Platform/WSL 环境仍待安装后验证；这不影响此前骨架验收。

## MeterGate｜企业服务计量与结算平台

### 项目约定

- 计划：[MeterGate 30 天计划](docs/plan.md)。
- 代码目录：本仓库根目录；启动说明见 [README](README.md)。
- 核心业务：企业与成员、API Key、套餐订阅、用量额度、账单、模拟支付和审计。
- 技术路线：FastAPI、Pydantic、PostgreSQL、SQLAlchemy、Alembic、Redis、Dramatiq；模块化单体。
- 首版限制：CNY 单币种、整数分金额、每月计费、套餐下周期变更、模拟支付。
- 关键设计：租户级幂等键、数据库条件扣减、周期价格快照、事务 Outbox；细节按原计划。

### 当前进度

- 已完成：第 01 天；配置、服务入口、路由、健康检查、独立依赖锁文件、范围文档、目录占位和工厂/生命周期测试。
- 当前任务：第 01 天验收已通过，等待开始第 02 天。
- 关键文件：`pyproject.toml`、`uv.lock`、`.python-version`、`.env.example`、`app/main.py`、`app/core/config.py`、`app/api/{router,health}.py`、`tests/test_app.py`、`docs/scope.md`、`README.md`。
- 已实现：`Settings`、`create_app()`、`lifespan()`、`GET /health/live`；配置用 `MG_` 前缀，数据库 URL 与 JWT 密钥使用 SecretStr。
- 验证（工作目录为本仓库根目录）：`uv run --locked --offline ruff check .`、`uv run --locked --offline ruff format --check .` 均通过；`uv run --locked --offline pytest -p no:cacheprovider` 为 **1 passed**。本机用本地 uv 的完整路径执行这些命令。
- 启动验证：实际启动 Uvicorn，在 8000 端口请求 `/health/live` 返回 200，`/openapi.json` 标题与健康路径正确；验证后已停止进程。
- 问题/待定项：数据库和 Redis 尚未配置/连接；`app/db` 等目录没有功能实现，Docker/Alembic 尚未安装或配置。

### 下一步：第 02 天

1. 读取计划第 02 天，保留现有工厂与独立配置，不重新生成骨架。
2. 将 SQLAlchemy、asyncpg、Alembic、Redis 等实际使用的依赖加入本项目并更新锁文件。
3. 实现 `app/db/base.py`、`app/db/session.py`、`get_session()`，配置 `migrations/env.py` 与首次迁移。
4. 创建 `deploy/compose.dev.yml` 启动 PostgreSQL、Redis；在 lifespan 初始化和释放实际连接池。
5. 新增 `/health/ready`，验证空数据库迁移、数据库停机时 ready=503/live=200、关闭连接池；尚未完成前不要把目录占位算成数据库功能。

## 最近记录

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
