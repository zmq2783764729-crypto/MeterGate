# MeterGate 第 01 天验收记录

验收日期：2026-10-12（Asia/Shanghai）。依据：[计划第 01 天](plan.md)。

结论：补齐范围文档与计划示例格式后，第 01 天交付通过复验，可以开始第 02 天。仅验收应用骨架，不代表计量、账单或数据库功能已实现。

## 逐项核对

| 要求 | 实际交付与验证 | 结果 |
|---|---|---|
| Python 工程与锁定依赖 | `pyproject.toml`、`.python-version`、`uv.lock`；Python 3.12.14，全新虚拟环境执行 `uv sync --locked --offline` 安装成功，锁文件一致性检查通过 | 通过 |
| 配置与集成占位 | `Settings` 使用 `MG_` 前缀及本项目 `.env`；PostgreSQL、Redis、JWT 占位为空，示例可直接加载；环境变量覆盖文件配置，非法环境名/日志级别被拒绝 | 通过 |
| 应用工厂与路由 | `create_app()`、`app/api/router.py`、`GET /health/live` 已实现；测试验证两份应用配置互不串用 | 通过 |
| 生命周期 | `lifespan()` 正常进入/退出；补充验证异常退出时也恢复 `started=False`。目前未连接外部资源，连接池管理属于第 02 天 | 通过 |
| 开发启动与真实 HTTP | 使用全新环境的 Python 启动 Uvicorn，监听 `127.0.0.1:65474`；健康返回 200，OpenAPI 标题与路径正确，`/docs` 返回 200；结束后已停止本次启动的进程 | 通过 |
| Ruff | 全项目 `ruff check .` 通过；`ruff format --check .` 通过 | 通过 |
| pytest | 全新环境执行现有测试，结果 `1 passed`；覆盖配置隔离、健康响应、测试密钥脱敏和生命周期结束 | 通过 |
| 首版闭环与计费规则 | `docs/scope.md` 明确闭环、费用公式、整数分、UTC 周期、时间归属、套餐快照、幂等、事务额度更新和 Outbox 规则 | 补齐后通过 |
| 凭据排除 | 已跟踪文件不含 `.env`、虚拟环境或运行数据；忽略规则验证通过，集成示例值为空，未发现高置信度私钥/GitHub token 特征；配置显示和健康响应不包含测试密钥 | 通过；不等同于全面密钥审计 |

健康接口实测响应：

```json
{"status":"ok","service":"MeterGate","version":"0.1.0"}
```

## 本次修正

1. 原 `docs/scope.md` 仅列设计关键词，未完整记录第 01 天要求的计费规则；已补齐。
2. 原 `docs/plan.md` 的 Python 示例缺少顶层函数间空行，导致完整格式检查失败；已修正。此前针对 `app` 与 `tests` 的格式通过不能代表整个项目通过，本次已重新检查全项目。
3. README 增加当前电脑的辅助 uv 路径与直接使用虚拟环境的启动方法，避免普通终端找不到 uv。

## 复验环境与命令

工作目录为 MeterGate 仓库根目录。使用独立的 `.local/day01-acceptance-venv`，从已有缓存离线安装，排除依赖旧 `.venv` 的影响；没有验证另一台电脑或在线下载。

```powershell
$env:UV_CACHE_DIR = Join-Path (Split-Path $PWD -Parent) '.local/uv-cache'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $PWD '.local/day01-acceptance-venv'
$env:UV_PYTHON_DOWNLOADS = 'never'
# 本机已有可用 Python 3.12；复验时显式指定其可执行文件。
& ../.local/bootstrap/bin/uv.exe sync --locked --offline --python 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& ../.local/bootstrap/bin/uv.exe lock --check --offline
& ../.local/bootstrap/bin/uv.exe run --locked --offline ruff check .
& ../.local/bootstrap/bin/uv.exe run --locked --offline ruff format --check .
& ../.local/bootstrap/bin/uv.exe run --locked --offline pytest -p no:cacheprovider
```

测试关闭缓存写入以避开当前沙箱的临时目录权限限制，不影响测试断言。配置及 HTTP 补充核验由父目录忽略的临时验收脚本执行，不是项目运行依赖。真实 HTTP 选择空闲端口，后续复验端口可不同。

本机 uv 尚未加入 PATH，日常启动按 README 的本机命令执行；其他电脑需安装 Python 3.12 与 uv。Docker/WSL 能否正常启动尚未复验，第 01 天不依赖 Docker。

本次修改仍在本地工作区，尚未提交或推送。下一步仍为第 02 天：数据库、Redis、迁移与就绪检查。
