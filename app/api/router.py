# 用途：汇总并注册 HTTP 路由，当前只挂载健康检查接口。
from fastapi import APIRouter

from app.api.health import router as health_router

router = APIRouter()
router.include_router(health_router)
