# 用途：用具备 usage:write 的 API Key 上下文和独立数据库会话接收用量事件。
from app.modules.api_keys.router import UsageWriteKeyDependency
from app.modules.metering.schemas import UsageIn, UsageResult
from app.modules.metering.service import ingest_usage
from app.modules.tenants.router import TenantSessionDependency


async def submit_usage(
    data: UsageIn, context: UsageWriteKeyDependency, session: TenantSessionDependency
) -> UsageResult:
    return await ingest_usage(session, context, data)
