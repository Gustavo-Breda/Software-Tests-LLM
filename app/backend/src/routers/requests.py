from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import *
from ..models import *
from ..schemas import *

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreateIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ServiceRequest:
    req = ServiceRequest(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        owner_id=current.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("", response_model=RequestListOut)
def list_requests(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    priority: RequestPriority | None = Query(default=None),
    scope: str = Query(default="own", pattern="^(own|all)$"),
) -> RequestListOut:
    stmt = select(ServiceRequest)
    if scope == "own":
        stmt = stmt.where(ServiceRequest.owner_id == current.id)
    if status_filter is not None:
        stmt = stmt.where(ServiceRequest.status == status_filter)
    if priority is not None:
        stmt = stmt.where(ServiceRequest.priority == priority)
    stmt = stmt.order_by(ServiceRequest.created_at.desc())
    items = list(db.scalars(stmt).all())
    return RequestListOut(items=[RequestOut.model_validate(r) for r in items], total=len(items))


@router.post("/{request_id}/cancel", response_model=RequestOut)
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada.")
    if req.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não pode cancelar uma solicitação de outro usuário.")
    if req.status not in (RequestStatus.ABERTA, RequestStatus.EM_ANALISE):
        raise HTTPException(status.HTTP_409_CONFLICT, "Somente solicitações 'aberta' ou 'em análise' podem ser canceladas.")
    req.status = RequestStatus.CANCELADA
    req.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(req)
    return req


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitação não encontrada.")
    if req.owner_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado.")
    return req
