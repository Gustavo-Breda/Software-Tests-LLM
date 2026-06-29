"""Service requests — US-03 (create), US-04 (list+filter), US-05 (cancel)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import (
    ServiceRequest, RequestStatus, RequestPriority, User,
)
from ..schemas import RequestCreateIn, RequestOut, RequestListOut


router = APIRouter(prefix="/api/requests", tags=["requests"])


# ---------------- US-03: Create ----------------
@router.post(
    "",
    response_model=RequestOut,
    status_code=status.HTTP_201_CREATED,
)
def create_request(
    payload: RequestCreateIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ServiceRequest:
    req = ServiceRequest(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=RequestStatus.ABERTA,   # auto-status (US-03)
        created_at=datetime.utcnow(),  # auto-date (US-03)
        owner_id=current.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


# ---------------- US-04: List + filter ----------------
@router.get("", response_model=RequestListOut)
def list_requests(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    status_filter: Optional[RequestStatus] = Query(default=None, alias="status"),
    priority: Optional[RequestPriority] = Query(default=None),
    scope: str = Query(default="own", pattern="^(own|all)$"),
) -> RequestListOut:
    """
    US-04: default returns the caller's own requests, newest first.
    Filters by status and priority are combinable. `scope=all` is provided
    so the same endpoint can support an "all requests" view if needed —
    the frontend defaults to scope=own per the criterion.
    """
    q = db.query(ServiceRequest)
    if scope == "own":
        q = q.filter(ServiceRequest.owner_id == current.id)
    if status_filter is not None:
        q = q.filter(ServiceRequest.status == status_filter)
    if priority is not None:
        q = q.filter(ServiceRequest.priority == priority)
    q = q.order_by(ServiceRequest.created_at.desc())

    items = q.all()
    # Empty result is *not* an error — frontend will render
    # "Nenhuma solicitação encontrada" while keeping the filter controls visible.
    return RequestListOut(items=[RequestOut.model_validate(r) for r in items], total=len(items))


# ---------------- US-05: Cancel ----------------
@router.post("/{request_id}/cancel", response_model=RequestOut)
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação não encontrada.",
        )
    # Ownership rule (US-05)
    if req.owner_id != current.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não pode cancelar uma solicitação de outro usuário.",
        )
    # Cancellable-status rule (US-05)
    if req.status not in (RequestStatus.ABERTA, RequestStatus.EM_ANALISE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Somente solicitações 'aberta' ou 'em análise' podem ser canceladas.",
        )
    req.status = RequestStatus.CANCELADA
    req.cancelled_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return req


# Helper for the frontend's confirmation dialog ("showing title" — US-05)
@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")
    if req.owner_id != current.id:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    return req
