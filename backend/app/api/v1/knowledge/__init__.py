"""Knowledge Base API — document upload, listing, and status tracking."""
import uuid
import aiofiles
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.models.knowledge import KnowledgeDocument, DocumentStatus
from app.models.user import User
from app.security.auth import get_current_user
from app.core.logging import logger

router = APIRouter()

UPLOAD_DIR = "uploads"
ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


async def _ingest_document_background(
    document_id: str,
    business_id: str,
    file_path: str,
    file_type: str,
):
    """Background task — run RAG ingestion after upload."""
    from app.database.session import AsyncSessionLocal
    from app.rag.pipeline import rag_pipeline

    async with AsyncSessionLocal() as db:
        try:
            if file_type == "pdf":
                chunks = await rag_pipeline.ingest_pdf(file_path, business_id, document_id, db)
            else:
                async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = await f.read()
                chunks = await rag_pipeline.ingest_document(business_id, document_id, content, db)

            logger.info(f"✅ Background ingestion complete: {document_id} → {chunks} chunks")
            await db.commit()
        except Exception as e:
            logger.error(f"Background ingestion failed for {document_id}: {e}")
            # Mark as failed
            from sqlalchemy import select
            r = await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(document_id))
            )
            doc = r.scalar_one_or_none()
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error = str(e)
                await db.commit()


@router.get("/public/list")
async def public_list_documents(db: AsyncSession = Depends(get_db)):
    """List knowledge documents — no auth, for dev dashboard."""
    from app.models.business import Business
    biz = (await db.execute(select(Business).limit(1))).scalar_one_or_none()
    if not biz:
        return []
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.business_id == biz.id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "file_name": d.file_name,
            "file_type": d.file_type,
            "file_size_bytes": d.file_size_bytes,
            "status": d.status.value,
            "chunk_count": d.chunk_count,
            "error": d.error,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.post("/public/upload")
async def public_upload_document(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document — no auth, for dev dashboard. Uses first business."""
    from app.models.business import Business
    biz = (await db.execute(select(Business).limit(1))).scalar_one_or_none()
    if not biz:
        raise HTTPException(status_code=404, detail="No business found. Create one first.")

    content_type = file.content_type or ""
    file_type = ALLOWED_TYPES.get(content_type)
    if not file_type:
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext in ("pdf", "txt", "csv", "docx"):
            file_type = ext
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4()}.{file_type}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    doc = KnowledgeDocument(
        business_id=biz.id,
        title=title,
        file_name=file.filename,
        file_url=file_path,
        file_type=file_type,
        file_size_bytes=len(content),
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    doc_id = str(doc.id)

    background_tasks.add_task(
        _ingest_document_background,
        document_id=doc_id,
        business_id=str(biz.id),
        file_path=file_path,
        file_type=file_type,
    )
    logger.info(f"📄 Public document uploaded: {doc_id} | {file.filename}")
    return {
        "id": doc_id,
        "title": title,
        "file_name": file.filename,
        "file_type": file_type,
        "status": "pending",
        "message": "Document uploaded. Ingestion started.",
    }


@router.delete("/public/{document_id}")
async def public_delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a document — no auth, for dev dashboard."""
    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.file_url and os.path.exists(doc.file_url):
        os.remove(doc.file_url)
    await db.delete(doc)
    return {"status": "deleted", "id": str(document_id)}


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    business_id: uuid.UUID = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a knowledge document (PDF, TXT, CSV).
    File is saved, a KnowledgeDocument record is created,
    and RAG ingestion is triggered as a background task.
    """
    # Validate file type
    content_type = file.content_type or ""
    file_type = ALLOWED_TYPES.get(content_type)
    if not file_type:
        # Try by extension
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext in ("pdf", "txt", "csv", "docx"):
            file_type = ext
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}. Allowed: PDF, TXT, CSV, DOCX"
            )

    # Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4()}.{file_type}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create DB record
    doc = KnowledgeDocument(
        business_id=business_id,
        title=title,
        file_name=file.filename,
        file_url=file_path,
        file_type=file_type,
        file_size_bytes=len(content),
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    doc_id = str(doc.id)

    # Trigger background ingestion
    background_tasks.add_task(
        _ingest_document_background,
        document_id=doc_id,
        business_id=str(business_id),
        file_path=file_path,
        file_type=file_type,
    )

    logger.info(f"📄 Document uploaded: {doc_id} | {file.filename} | {len(content)} bytes")

    return {
        "id": doc_id,
        "title": title,
        "file_name": file.filename,
        "file_type": file_type,
        "status": "pending",
        "message": "Document uploaded. Ingestion started in background.",
    }


@router.get("")
async def list_documents(
    business_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge documents for a business."""
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.business_id == business_id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "file_name": d.file_name,
            "file_type": d.file_type,
            "file_size_bytes": d.file_size_bytes,
            "status": d.status.value,
            "chunk_count": d.chunk_count,
            "error": d.error,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/{document_id}/status")
async def document_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll ingestion status of a document."""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": str(doc.id),
        "status": doc.status.value,
        "chunk_count": doc.chunk_count,
        "error": doc.error,
    }


@router.post("/search")
async def search_knowledge(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test endpoint — run a semantic search against the knowledge base.
    body: {business_id, query, top_k}
    """
    from app.tools.search_tools import search_knowledge as _search
    result = await _search(
        query=body.get("query", ""),
        business_id=body.get("business_id", ""),
        db=db,
        top_k=body.get("top_k", 5),
    )
    return result


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and all its chunks from the knowledge base."""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file
    if doc.file_url and os.path.exists(doc.file_url):
        os.remove(doc.file_url)

    await db.delete(doc)
    return {"status": "deleted", "id": str(document_id)}
