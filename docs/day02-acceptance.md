# MeterGate 第 02 天验收记录

日期：2026-10-15（Asia/Shanghai）。依据：[开发计划第 02 天](plan.md)。

结论：第 02 天通过。完成 PostgreSQL/Redis 连接资源、请求会话、Alembic 迁移与就绪检查；业务表与计费业务尚未实现。

| 验收项 | 实际证据 | 结果 |
|---|---|---|
| 开发数据服务 | 用户启动 PostgreSQL、Redis 并验证 healthy、SELECT 1 和 PONG | 通过 |
| 数据库基础层 | Base、异步 engine、async_sessionmaker、get_session；每请求独立会话，service 显式决定事务提交 | 通过 |
| 资源生命周期 | 独立应用真实连接 PostgreSQL/Redis；会话结束归还连接，lifespan 退出后借用的 asyncpg 与 Redis 连接关闭 | 通过 |
| 未提交事务 | 两个 Session 分别查询成功；第一个 Session 创建临时表但不提交，退出后从同一物理连接查询确认临时表不存在 | 通过 |
| 开发库迁移 | 用户生成并执行 0001_baseline；助手核对 alembic current 与版本表均为 0001_baseline | 通过 |
| 独立空数据库迁移 | 新建专属测试库，迁移前 public 表数为 0；upgrade head 后只有 alembic_version，版本为 0001_baseline | 通过 |
| 重复执行迁移 | 测试库再次 upgrade head 成功，版本仍为 0001_baseline | 通过 |
| 数据库停机 | 用户实际停止 PostgreSQL，截图显示 live=200、ready=503，数据库不可用、Redis 正常 | 通过 |
| 数据库恢复 | 用户启动 PostgreSQL 后，未重启 FastAPI，ready 恢复 200；助手最后读取当前 live/ready 均为 200 | 通过 |
| 当前完整测试 | `.venv/Scripts/python.exe -m pytest -p no:cacheprovider`：11 passed，包含当前中文响应预期 | 通过 |
| 工程检查 | 锁文件一致性、全项目 Ruff 检查与格式检查、git diff --check | 通过 |

## 迁移的实际边界

`0001_baseline` 的 upgrade/downgrade 都是空操作，本次验证的是迁移工具链与版本记录。Alembic 建立版本表，不代表企业、用户、套餐或账单表已经实现。后续业务模型通过新版本迁移添加，不重新生成或修改已应用的初始版本。

## 独立测试环境与清理

本次测试库为 `metergate_day02_acceptance_0715b7c95022`，位于本项目开发 PostgreSQL 容器。使用进程环境变量覆盖数据库名，没有修改用户 `.env` 或开发库；资源关闭后确认测试库剩余连接为 0，随后删除测试库并确认已不存在。用户的开发服务和容器保持运行。

临时验收脚本与原始结果保存在父目录忽略的 `.local` 中，不是应用运行依赖。用户停库/恢复截图与助手独立测试分别提供证据，没有为重复演示再停止用户数据库。

Windows 沙箱的 asyncio 回环 socket 限制此前已确认，本次完整测试与真实连接验收在正常执行环境中运行。当前电脑使用虚拟环境的 `python.exe -m ...` 调用工具，避开曾出现的 uv trampoline 入口问题。

下一步为第 03 天：在已有中文错误处理上补充领域错误规范、request_id 和结构化日志。唯一进度记录为根目录 [progress.md](../progress.md)。本轮修改尚未提交或推送。
