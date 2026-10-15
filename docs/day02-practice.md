# 第 02 天动手练习：数据库连接与迁移

本文件解释操作与代码，实际完成情况只记录在根目录 progress.md。采取逐步练习：用户执行和观察结果，助手检查结果并继续实现下一部分。

## 练习 1：先让 PostgreSQL 与 Redis 运行

FastAPI 是接收 HTTP 请求的应用，PostgreSQL 是保存业务数据的独立服务，Redis 是后续缓存与队列使用的独立服务。先确认这两个服务能运行，再写 Python 连接代码，方便区分环境问题与代码问题。

启动配置位于 `deploy/compose.dev.yml`。2026-10-14 用户完成本练习，助手复核两个服务 healthy、SQL 返回 1、Redis 返回 PONG。

| 字段 | 含义 |
|---|---|
| `services` | 本次要运行的服务：postgres 和 redis |
| `image` | 容器使用的官方软件镜像；固定大版本，补丁仍可能更新 |
| `environment` | PostgreSQL 首次初始化时使用的用户、密码和数据库名 |
| `ports` | `本机地址:本机端口:容器端口`；本机连接 PostgreSQL 用 55432，Redis 用 56379 |
| `volumes` | 数据保存在 Docker 管理的数据卷中，容器重建时仍可保留 |
| `healthcheck` | 定期检查服务是否可响应，而不是只看容器进程是否启动 |

配置中的 `metergate_dev_only` 是仅用于本机开发的示例密码，端口仅绑定本机回环地址；部署时另行配置凭据。此 Compose 暂时只启动数据服务，FastAPI 继续由本机 Python 运行。

### 用户操作

1. 手动打开 Docker Desktop，等待引擎运行；在 PowerShell 执行 `docker version`，确认输出同时包含 Client 和 Server。如果只有 Client 或出现 WSL/虚拟化报错，先提供错误信息，暂不继续数据库启动。
2. 引擎正常后执行：

```powershell
Set-Location 'C:/Users/Administrator/Documents/ChatGPT/My_FastApi_Agent_Project/metergate'
docker compose -f deploy/compose.dev.yml up -d --wait
docker compose -f deploy/compose.dev.yml ps
```

第一次执行需要联网下载两个镜像。`-f` 指定配置，`-d` 表示后台运行，`--wait` 等待服务达到健康状态。

3. 两个服务都 healthy 后，进一步验证：

```powershell
docker compose -f deploy/compose.dev.yml exec -T postgres psql -U metergate -d metergate -c 'SELECT 1;'
docker compose -f deploy/compose.dev.yml exec -T redis redis-cli ping
```

预期：SQL 返回数字 1，Redis 返回 PONG。把 `ps` 与这两条验证结果提供给助手，继续下一部分。

需要临时停服务时使用 `docker compose -f deploy/compose.dev.yml stop`。数据存在本机 Docker 数据卷，不随 GitHub 同步。

## 练习 2：连接 Python 应用

本阶段助手已安装并锁定：SQLAlchemy 2.0.54、asyncpg 0.32.0、Alembic 1.20.0、redis-py 8.1.0。Alembic 目前只是安装，迁移还未配置。

### 代码如何配合

1. `app/db/base.py` 提供 ORM 模型基类。将来业务模型继承它，Alembic 读取 `Base.metadata` 了解表结构；现在不创建业务表，也不在应用启动时调用 create_all。
2. `app/db/session.py` 创建异步 engine 和 sessionmaker。engine 管理连接池，sessionmaker 每次调用产生一个新 Session。`pool_pre_ping=True` 在取出连接时检查其是否有效；`expire_on_commit=False` 避免提交后读取已有 ORM 字段时自动触发额外加载。
3. `get_session()` 用 `async with` 提供请求级会话，结束后释放连接，未提交事务回滚。它不会自动提交；后续 service 可以用 `async with session.begin()` 组织一整笔业务事务。不要让多个并发任务共用一个 Session。依据：[SQLAlchemy 异步会话](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)。
4. `app/main.py` 的 lifespan 创建连接资源并存入当前应用的 state。`AsyncExitStack` 为每份资源登记清理，确保部分初始化失败或某一项清理失败时，仍尝试释放其他已创建资源。
5. 连接按需建立：应用启动并不代表数据库可用。`/health/live` 检查应用响应；`/health/ready` 并行执行数据库 `SELECT 1` 与 Redis `PING`，限制检查时间，任一项失败返回 503，响应不包含连接凭据。

### 用户操作

在 MeterGate 根目录执行以下命令；已有 `.env` 时不覆盖：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

打开 `.env`，把两个连接变量填成下面的值，其他配置保持原样：

```dotenv
MG_DATABASE_URL=postgresql+asyncpg://metergate:metergate_dev_only@127.0.0.1:55432/metergate
MG_REDIS_URL=redis://127.0.0.1:56379/0
```

这是前一步 Compose 使用的本机开发账号；若自行修改过数据库密码，使用初始化数据库时的实际值。

数据库地址中 `postgresql+asyncpg` 表示数据库类型与异步驱动；随后是用户名、密码、本机地址、映射端口、数据库名。Redis URL 最后的 `/0` 是逻辑数据库编号。因为 Python 应用运行在本机，所以使用 `127.0.0.1`；未来应用放入容器时需要改用容器网络里的服务名。

启动应用：

```powershell
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

保留启动窗口，另开一个 PowerShell 在 MeterGate 根目录验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/health/ready | ConvertTo-Json
```

预期 ready 返回：

```json
{
  "status": "已就绪",
  "checks": {"database": "正常", "redis": "正常"}
}
```

把 ready 的输出提供给助手，不需要发送 `.env`。`未配置` 表示相应连接地址没有加载；`不可用` 表示相应探针失败，可能是地址、认证、服务状态或超时问题。JWT 暂时无需填写。

用户可见状态与错误提示统一使用中文，接口字段名和 URL 保持原样。live 的状态为 `正常`；ready 的状态为 `已就绪` 或 `未就绪`，检查项为 `正常`、`不可用` 或 `未配置`。这替换了早期英文状态值，脚本若比较英文值需要同步修改。

### 助手已执行的验证

- 测试：8 passed，覆盖未配置、正常就绪、数据库失败、Redis 失败、探针超时和正常/异常资源清理。
- 真实开发容器：独立 Session 的 SELECT 1、临时表事务回滚、连接归还、lifespan 关闭 PostgreSQL/Redis 连接验证通过。
- 实际启动 Uvicorn，在本次随机端口 51235 上 ready=200、live=200。使用进程内测试配置，没有替用户修改 `.env`；验收进程已停止，用户容器保持运行。
- 使用拒绝连接的数据库端口验证 ready=503/live=200；这不替代下一练习实际停库的验收。
- 沙箱内 asyncio 创建本机回环 socket 时阻塞，正常执行环境测试通过；本机 uv 的 pytest 命令入口还出现 trampoline 错误，验收采用 `.venv/Scripts/python.exe -m pytest -p no:cacheprovider`。未为避开环境问题改写应用行为。

## 练习 3：迁移与实际故障验证（已通过）

2026-10-15，用户生成并执行 0001_baseline，助手核对数据库版本记录通过。用户实际停止 PostgreSQL 后 ready=503、live=200，再启动数据库后 ready 恢复 200。

收尾完成：当前完整测试 11 passed，Ruff 与锁文件检查通过；独立空测试库迁移、会话回滚、连接关闭通过，测试库已删除。第 02 天验收通过，进度在根目录 progress.md 更新为 2 / 30，详细证据见 [验收记录](day02-acceptance.md)。

参考：[Docker Compose 就绪检查](https://docs.docker.com/compose/how-tos/startup-order/)、[PostgreSQL 官方镜像](https://hub.docker.com/_/postgres)、[Redis 官方镜像](https://hub.docker.com/_/redis)。
