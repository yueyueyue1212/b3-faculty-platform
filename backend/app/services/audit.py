from sqlalchemy.orm import Session

from ..models import AuditLog, User


def write_audit(
    db: Session,
    user: User | None,
    action: str,
    resource_type: str,
    resource_id=None,
    detail: str = "",
    ip: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "system",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            detail=detail[:2000],
            ip=ip,
        )
    )
    db.commit()
