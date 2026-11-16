# 用途：根据账期快照与成功用量计算基础费、用量费和明细。
from app.modules.billing.schemas import InvoiceDraft, InvoiceLine
from app.modules.subscriptions.models import PeriodTerms


def calculate_invoice(snapshot: PeriodTerms, total_quantity: int) -> InvoiceDraft:
    if type(total_quantity) is not int or total_quantity < 0:
        raise ValueError("用量必须为非负整数")
    base = snapshot.base_fee_cents
    unit = snapshot.unit_price_cents
    usage = unit * total_quantity
    return InvoiceDraft(
        base_fee_cents=base,
        usage_fee_cents=usage,
        total_cents=base + usage,
        items=(
            InvoiceLine(
                kind="base",
                plan_version_id=snapshot.plan_version_id,
                quantity=1,
                unit_price_cents=base,
                amount_cents=base,
            ),
            InvoiceLine(
                kind="usage",
                plan_version_id=snapshot.plan_version_id,
                quantity=total_quantity,
                unit_price_cents=unit,
                amount_cents=usage,
            ),
        ),
    )
