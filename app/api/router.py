# 用途：为独立应用工厂复制已声明的 HTTP 接口，保持依赖覆盖与应用配置隔离。
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute


def copy_routes(target: FastAPI, source: FastAPI) -> None:
    # 只复制业务接口，不重复添加文档路由；include_router 会绑定目标应用的依赖覆盖。
    routes = [route for route in source.routes if isinstance(route, APIRoute)]
    target.include_router(APIRouter(routes=routes))
