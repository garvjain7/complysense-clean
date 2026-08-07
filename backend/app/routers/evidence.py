# Use: Router for uploading and reviewing evidence files.

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.database import get_db_session
from app.domain.rbac import PermissionKey, RoleName
from app.mongodb import get_mongo_database
from app.repositories.notification import NotificationRepository
from app.schemas.auth import UserContext

router = APIRouter(prefix="/evidence", tags=["evidence"])
GRIDFS_EVIDENCE_PREFIX = "mongodb://gridfs/evidence/"


async def _store_evidence_file(
    *,
    evidence_id: str,
    institution_id: str,
    file_name: str,
    content: bytes,
    content_type: str | None,
    control_id: str,
    assignment_id: str | None,
) -> str:
    database = get_mongo_database()
    bucket = AsyncIOMotorGridFSBucket(database, bucket_name="evidence_files")
    gridfs_id = await bucket.upload_from_stream(
        file_name,
        content,
        metadata={
            "evidence_id": evidence_id,
            "institution_id": institution_id,
            "control_id": control_id,
            "assignment_id": assignment_id,
            "content_type": content_type,
        },
    )
    return f"{GRIDFS_EVIDENCE_PREFIX}{gridfs_id}"


async def _read_evidence_file(file_path: str) -> bytes:
    database = get_mongo_database()
    bucket = AsyncIOMotorGridFSBucket(database, bucket_name="evidence_files")
    gridfs_id = file_path.removeprefix(GRIDFS_EVIDENCE_PREFIX)
    stream = await bucket.open_download_stream(ObjectId(gridfs_id))
    return await stream.read()


@router.get("", summary="List evidence documents for the current institution")
async def list_evidence(
    user_ctx: Annotated[UserContext, Depends(require_permission(PermissionKey.VIEW_EVIDENCE))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    query = """
        select evidence_id, control_id, file_name, approval_status, file_size_kb, uploaded_at, description, assignment_id, department_id
        from evidence_documents
        where institution_id = :inst_id
        order by uploaded_at desc
    """
    res = await session.execute(text(query), {"inst_id": user_ctx.institution_id})
    rows = res.mappings().all()
    return [
        {
            "evidence_id": str(row["evidence_id"]),
            "control_id": row["control_id"],
            "assignment_id": str(row["assignment_id"]) if row["assignment_id"] else None,
            "department_id": str(row["department_id"]) if row["department_id"] else None,
            "file_name": row["file_name"],
            "approval_status": row["approval_status"],
            "file_size_kb": row["file_size_kb"],
            "uploaded_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None,
            "description": row["description"],
        }
        for row in rows
    ]


@router.post("", status_code=201, summary="Upload evidence for a control assignment")
async def upload_evidence(
    user_ctx: Annotated[UserContext, Depends(require_permission(PermissionKey.UPLOAD_EVIDENCE))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    control_id: str = Form(...),
    assignment_id: str | None = Form(None),
    description: str | None = Form(None),
) -> dict[str, Any]:
    if assignment_id is not None:
        assignment_id = assignment_id.strip() or None
    if description is not None:
        description = description.strip() or None

    if user_ctx.active_role_name not in {RoleName.DEPARTMENT_REVIEWER, RoleName.IT_SECURITY_OFFICER, RoleName.COMPLIANCE_OFFICER}:
        raise HTTPException(status_code=403, detail="Only department reviewers and security/compliance staff can upload evidence")

    if assignment_id:
        assignment_check = await session.execute(
            text("select assignment_id from control_assignments where assignment_id = :assignment_id and institution_id = :inst_id"),
            {"assignment_id": assignment_id, "inst_id": user_ctx.institution_id},
        )
        if not assignment_check.mappings().first():
            raise HTTPException(status_code=404, detail="Control assignment not found")

    safe_name = Path(file.filename or "evidence.bin").name
    safe_name = safe_name.replace(" ", "_")
    evidence_id = uuid4()
    content = await file.read()
    stored_path = await _store_evidence_file(
        evidence_id=str(evidence_id),
        institution_id=str(user_ctx.institution_id),
        file_name=safe_name,
        content=content,
        content_type=file.content_type,
        control_id=control_id,
        assignment_id=assignment_id,
    )

    department_id = None
    if assignment_id:
        assignment_row = await session.execute(
            text("select department_id from control_assignments where assignment_id = :assignment_id and institution_id = :inst_id"),
            {"assignment_id": assignment_id, "inst_id": user_ctx.institution_id},
        )
        assignment_data = assignment_row.mappings().first()
        department_id = assignment_data["department_id"] if assignment_data else None

    res = await session.execute(
        text(
            """
            insert into evidence_documents (
                evidence_id, institution_id, control_id, assignment_id, department_id, file_name, file_path, mime_type, file_size_kb, description, uploaded_by, approval_status
            ) values (
                :evidence_id, :inst_id, :control_id, :assignment_id, :department_id, :file_name, :file_path, :mime_type, :file_size_kb, :description, :uploaded_by, 'pending'
            ) returning evidence_id, file_name, approval_status, file_size_kb, uploaded_at
            """
        ),
        {
            "evidence_id": evidence_id,
            "inst_id": user_ctx.institution_id,
            "control_id": control_id,
            "assignment_id": assignment_id,
            "department_id": department_id,
            "file_name": safe_name,
            "file_path": stored_path,
            "mime_type": file.content_type,
            "file_size_kb": max(1, len(content) // 1024),
            "description": description,
            "uploaded_by": user_ctx.user_id,
        },
    )
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to save evidence")

    try:
        if assignment_id:
            assignment_res = await session.execute(
                text(
                    "select assigned_to from control_assignments where assignment_id = :assignment_id and institution_id = :inst_id"
                ),
                {"assignment_id": assignment_id, "inst_id": user_ctx.institution_id},
            )
            assignment_row = assignment_res.mappings().first()
            assigned_to = assignment_row["assigned_to"] if assignment_row else None
            if assigned_to:
                await NotificationRepository(session).create(
                    institution_id=str(user_ctx.institution_id),
                    user_id=str(assigned_to),
                    title="New evidence uploaded",
                    message=f"Evidence '{safe_name}' was uploaded for review.",
                    notification_type="evidence_approved",
                    related_entity_type="evidence",
                )
        from app.repositories.audit import AuditLogRepository
        await AuditLogRepository(session).write(
            institution_id=user_ctx.institution_id,
            user_id=user_ctx.user_id,
            active_role_id=user_ctx.active_role_id,
            action_type="evidence_uploaded",
            entity_type="evidence",
            entity_id=str(row["evidence_id"]),
            action_details={"file_name": safe_name, "control_id": control_id},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return {
        "evidence_id": str(row["evidence_id"]),
        "file_name": row["file_name"],
        "approval_status": row["approval_status"],
        "file_size_kb": row["file_size_kb"],
        "uploaded_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None,
    }


@router.get("/{evidence_id}", summary="Get a single evidence document")
async def get_evidence(
    evidence_id: str,
    user_ctx: Annotated[UserContext, Depends(require_permission(PermissionKey.VIEW_EVIDENCE))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    query = """
        select evidence_id, control_id, file_name, approval_status, file_size_kb, uploaded_at, description, assignment_id, department_id
        from evidence_documents
        where evidence_id = :evidence_id
          and institution_id = :inst_id
    """
    res = await session.execute(text(query), {"evidence_id": evidence_id, "inst_id": user_ctx.institution_id})
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {
        "evidence_id": str(row["evidence_id"]),
        "control_id": row["control_id"],
        "assignment_id": str(row["assignment_id"]) if row["assignment_id"] else None,
        "department_id": str(row["department_id"]) if row["department_id"] else None,
        "file_name": row["file_name"],
        "approval_status": row["approval_status"],
        "file_size_kb": row["file_size_kb"],
        "uploaded_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None,
        "description": row["description"],
    }


@router.get("/{evidence_id}/download", summary="Download an evidence file")
async def download_evidence(
    evidence_id: str,
    user_ctx: Annotated[UserContext, Depends(require_permission(PermissionKey.VIEW_EVIDENCE))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    res = await session.execute(
        text(
            "select file_path, file_name, mime_type from evidence_documents where evidence_id = :evidence_id and institution_id = :inst_id"
        ),
        {"evidence_id": evidence_id, "inst_id": user_ctx.institution_id},
    )
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")
    file_path = row["file_path"]
    if not file_path:
        raise HTTPException(status_code=404, detail="File not available")
    if str(file_path).startswith(GRIDFS_EVIDENCE_PREFIX):
        content = await _read_evidence_file(str(file_path))
        return Response(
            content=content,
            media_type=row.get("mime_type") or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{row.get("file_name") or "evidence.bin"}"'},
        )

    p = Path(file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Stored file missing on server")
    return FileResponse(str(p), filename=row.get("file_name") or p.name, media_type="application/octet-stream")
