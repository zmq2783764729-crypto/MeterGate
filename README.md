# MeterGate｜企业服务计量与结算平台

企业与成员、API Key、套餐订阅、用量额度、账单、模拟支付和审计。

当前完成第 01 天应用骨架。已具备环境配置、FastAPI 工厂、生命周期和健康接口；数据库与业务模块尚未实现。

## 启动

需要 Python 3.12 与 uv。在本项目目录中执行：

```powershell
uv sync --locked
Copy-Item .env.example .env
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

若已经有 `.env`，保留原配置，不重复覆盖。当前没有必须填写的密钥，也不要求数据库运行。

- 健康接口：`http://127.0.0.1:8000/health/live`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`
- 接口只反映应用存活；数据库就绪检查安排在第 02 天。

## 检查

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## 结构与配置

`app/core` 管理配置；`app/api` 汇总路由；`app/db`、`dependencies`、`middleware`、`modules`、`integrations`、`workers` 和 `observability` 是后续实现入口。`migrations`、`scripts`、`deploy` 暂存目录占位，没有可执行迁移或部署配置。

配置变量使用 `MG_` 前缀，从本项目 `.env` 或环境读取。数据库 URL 和 JWT 密钥采用 SecretStr，禁止向日志输出原始值。`.env` 不提交 Git。

后续依据 [开发计划](docs/plan.md) 推进；唯一进度记录为 [progress.md](progress.md)。


## GitHub 同步

本文件所在目录是独立仓库根目录，Git 命令在这里执行。仓库包含自己的计划和 progress.md，无需下载另一个项目。创建空的 GitHub 仓库后配置 origin，首次推送使用 `git push -u origin HEAD`。
