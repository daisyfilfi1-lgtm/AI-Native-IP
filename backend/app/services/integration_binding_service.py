import uuid

from sqlalchemy.orm import Session

from app.db.models import IntegrationBinding


def get_binding(db: Session, integration: str, ip_id: str) -> IntegrationBinding | None:
    return (
        db.query(IntegrationBinding)
        .filter(
            IntegrationBinding.integration == integration,
            IntegrationBinding.ip_id == ip_id,
        )
        .first()
    )


def upsert_binding(
    db: Session,
    *,
    integration: str,
    ip_id: str,
    external_id: str,
    external_name: str | None = None,
    extra: dict | None = None,
) -> IntegrationBinding:
    row = get_binding(db, integration, ip_id)
    if row:
        row.external_id = external_id
        row.external_name = external_name
        row.extra = extra or {}
        db.flush()
        db.commit()
        return row

    row = IntegrationBinding(
        id=f"bind_{uuid.uuid4().hex[:16]}",
        integration=integration,
        ip_id=ip_id,
        external_id=external_id,
        external_name=external_name,
        extra=extra or {},
    )
    db.add(row)
    db.flush()
    db.commit()
    return row
