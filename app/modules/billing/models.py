# 用途：按账期保存后台生成的结算输入，确保重复投递只保存一次。
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SettlementInput(Base):
    __tablename__ = "settlement_inputs"

    period_id: Mapped[UUID] = mapped_column(
        ForeignKey("billing_periods.id", ondelete="RESTRICT"), primary_key=True
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="RESTRICT"), unique=True
    )
    total_quantity: Mapped[int] = mapped_column(BigInteger)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
