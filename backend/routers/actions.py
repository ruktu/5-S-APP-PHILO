from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Action
from utils import apply_fields, row_to_dict

router = APIRouter()

_ALLOWED_FIELDS = {c.name for c in Action.__table__.columns}


@router.get("/api/actions")
def list_actions(db: Session = Depends(get_db)):
    rows = db.query(Action).order_by(Action.openDate.desc()).all()
    return {"data": [row_to_dict(r) for r in rows]}


@router.post("/api/actions/upsert")
def upsert_actions(payload: dict = Body(...), db: Session = Depends(get_db)):
    items = payload.get("items", [])
    count = 0
    for item in items:
        filtered = {k: v for k, v in item.items() if k in _ALLOWED_FIELDS}
        if not filtered.get("actionId"):
            continue
        db.merge(Action(**filtered))
        count += 1
    db.commit()
    return {"ok": True, "count": count}


@router.patch("/api/actions/{action_id}")
def update_action(action_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(Action, action_id)
    if not obj:
        raise HTTPException(404, "not found")
    apply_fields(obj, payload, {"owner", "status", "dueDate"})
    db.commit()
    return {"data": row_to_dict(obj)}


@router.delete("/api/actions/{action_id}")
def delete_action(action_id: str, auditId: str | None = Query(None), db: Session = Depends(get_db)):
    obj = db.get(Action, action_id)
    if obj and (auditId is None or obj.auditId == auditId):
        db.delete(obj)
        db.commit()
    return {"ok": True}
