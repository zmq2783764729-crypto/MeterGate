# MeterGate｜企业服务计量与结算平台

企业与成员、API Key、套餐订阅、用量额度、账单、模拟支付和审计。

当前完成第 01、02 天。已实现环境配置、FastAPI 工厂、PostgreSQL/Redis 连接生命周期、请求会话、live/ready 健康接口和 Alembic 首次版本基线；空库迁移与停库恢复验收通过。业务表与业务模块尚未实现。

## 启动

需要 Python 3.12 与 uv。在本项目目录中执行：

```powershell
uv sync --locked
Copy-Item .env.example .env
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

若已经有 `.env`，保留原配置，不重复覆盖。不填数据库和 Redis 地址时仍可运行应用，live=200、ready=503；要使 ready=200，按 [第 02 天练习](docs/day02-practice.md) 启动数据服务并填写连接地址。JWT 暂时无需填写。

本机的 uv 位于父目录辅助工具中，尚未加入 PATH。当前电脑可在本项目目录执行：

```powershell
& ../.local/bootstrap/bin/uv.exe sync --locked
& ../.local/bootstrap/bin/uv.exe run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

已建立 `.venv` 时也可以直接启动：

```powershell
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

父目录辅助工具不随 GitHub 同步；其他电脑先安装 Python 3.12 与 uv，再使用本节开头的通用命令。

- 健康接口：`http://127.0.0.1:8000/health/live`
- 就绪接口：`http://127.0.0.1:8000/health/ready`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`
- live 反映应用存活；ready 实际检查 PostgreSQL 与 Redis，任一项未配置或不可用返回 503。

用户可见的健康状态和错误提示统一使用中文，字段名与 HTTP 状态码保持原样。例如 ready 正常时返回 `{"status":"已就绪","checks":{"database":"正常","redis":"正常"}}`，live 的 `status` 为 `正常`。依赖故障返回 `未就绪`，检查项为 `不可用` 或 `未配置`；按英文状态值判断的旧脚本需同步调整。

## 检查

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

当前 Windows 工具环境若出现 uv trampoline 命令入口错误，可直接执行 `& ./.venv/Scripts/python.exe -m pytest`；`-p no:cacheprovider` 可用于无需写入测试缓存的验收。

## 结构与配置

`app/core` 管理配置和中文错误响应；`app/api` 汇总路由；`app/db` 提供模型基类、异步连接池与会话；`dependencies`、`middleware`、`modules`、`integrations`、`workers` 和 `observability` 是后续实现入口。`migrations` 包含异步迁移环境与 0001_baseline，`scripts` 暂存目录占位。`deploy/compose.dev.yml` 提供本机 PostgreSQL 与 Redis 启动配置，操作见 [第 02 天动手练习](docs/day02-practice.md)。

配置变量使用 `MG_` 前缀，从本项目 `.env` 或环境读取。数据库 URL 和 JWT 密钥采用 SecretStr，禁止向日志输出原始值。`.env` 不提交 Git。

后续依据 [开发计划](docs/plan.md) 推进；唯一进度记录为 [progress.md](progress.md)。

第 01 天逐项复验见 [验收记录](docs/day01-acceptance.md)。
第 02 天迁移、连接与故障恢复验收见 [验收记录](docs/day02-acceptance.md)。


## 代码阅读

每个 Python 文件开头都有一条中文 `# 用途：` 注释。全部说明汇总在 [代码文件用途汇总](docs/code-map.md)，包含已有实现、包入口和未实现的预留模块。

## GitHub 同步

本文件所在目录是独立仓库根目录，Git 命令在这里执行。仓库包含自己的计划和 progress.md，无需下载另一个项目。

远端：[MeterGate](https://github.com/zmq2783764729-crypto/MeterGate)。本机工作分支 codex/initial 跟踪远端 main，已配置直接 git push 使用该上游。换电脑时 clone 本仓库，按当前分支执行 `git pull --ff-only`；开发结束时更新 progress.md，并提交、推送。
