# 用途：提供只读管理页和同源脚本，业务数据继续使用受保护的租户接口。
from fastapi.responses import FileResponse

from app.core.config import PROJECT_ROOT

TEMPLATES = PROJECT_ROOT / "app" / "templates"


def dashboard_page() -> FileResponse:
    return FileResponse(
        TEMPLATES / "dashboard.html",
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
        },
    )


def dashboard_script() -> FileResponse:
    return FileResponse(
        TEMPLATES / "dashboard.js",
        media_type="text/javascript; charset=utf-8",
        headers={"X-Content-Type-Options": "nosniff"},
    )
