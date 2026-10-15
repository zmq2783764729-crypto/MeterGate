# 用途：提供 SQLAlchemy 模型基类，供后续业务模型与 Alembic 共享表结构元数据。
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
