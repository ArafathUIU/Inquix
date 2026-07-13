from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import KnowledgeBase, Document
from app.schemas import KBCreate, KBResponse

router = APIRouter()


@router.post("/kb", response_model=KBResponse)
async def create_kb(data: KBCreate, db: AsyncSession = Depends(get_db)):
    kb = KnowledgeBase(name=data.name, description=data.description)
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return KBResponse(id=kb.id, name=kb.name, description=kb.description, created_at=kb.created_at, document_count=0)


@router.get("/kb", response_model=list[KBResponse])
async def list_kbs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
    kbs = result.scalars().all()

    responses = []
    for kb in kbs:
        count_result = await db.execute(select(func.count(Document.id)).where(Document.kb_id == kb.id))
        doc_count = count_result.scalar() or 0
        responses.append(KBResponse(
            id=kb.id, name=kb.name, description=kb.description,
            created_at=kb.created_at, document_count=doc_count,
        ))
    return responses


@router.get("/kb/{kb_id}", response_model=KBResponse)
async def get_kb(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    count_result = await db.execute(select(func.count(Document.id)).where(Document.kb_id == kb.id))
    return KBResponse(
        id=kb.id, name=kb.name, description=kb.description,
        created_at=kb.created_at, document_count=count_result.scalar() or 0,
    )


@router.delete("/kb/{kb_id}")
async def delete_kb(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    await db.delete(kb)
    await db.commit()
    return {"status": "deleted"}
