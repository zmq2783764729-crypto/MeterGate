# 用途：保护已生成的计费快照并重新投递已有结算输入。
from alembic import op

revision = "0013_invoice_delivery"
down_revision = "0012_invoices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION protect_invoice_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_TABLE_NAME = 'invoices' AND TG_OP = 'UPDATE' THEN
                IF (to_jsonb(NEW) - 'status') = (to_jsonb(OLD) - 'status')
                   AND (NEW.status = OLD.status OR
                        (OLD.status = 'open' AND NEW.status IN ('paid', 'void'))) THEN
                    RETURN NEW;
                END IF;
            END IF;
            RAISE EXCEPTION 'invoice snapshot is immutable' USING ERRCODE = '55000';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER protect_invoice_snapshot BEFORE UPDATE OR DELETE ON invoices
        FOR EACH ROW EXECUTE FUNCTION protect_invoice_snapshot()
    """)
    op.execute("""
        CREATE TRIGGER protect_invoice_items BEFORE UPDATE OR DELETE ON invoice_items
        FOR EACH ROW EXECUTE FUNCTION protect_invoice_snapshot()
    """)
    op.execute("""
        UPDATE outbox_events AS e SET published_at = NULL, failed_at = NULL, attempts = 0,
          last_error = NULL, next_attempt_at = now()
        FROM settlement_inputs AS s
        WHERE e.id = s.event_id AND NOT EXISTS (
            SELECT 1 FROM invoices AS i WHERE i.period_id = s.period_id
        )
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER protect_invoice_items ON invoice_items")
    op.execute("DROP TRIGGER protect_invoice_snapshot ON invoices")
    op.execute("DROP FUNCTION protect_invoice_snapshot()")
