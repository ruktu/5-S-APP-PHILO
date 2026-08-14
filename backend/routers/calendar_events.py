import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import CalendarEvent
from utils import apply_fields, row_to_dict

router = APIRouter()


@router.get("/api/calendar_events")
def list_calendar_events(db: Session = Depends(get_db)):
    rows = db.query(CalendarEvent).all()
    return {"data": [row_to_dict(r) for r in rows]}


@router.post("/api/calendar_events")
def create_calendar_event(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = CalendarEvent(
        audit_date=payload.get("audit_date"),
        area_name=payload.get("area_name"),
        status=payload.get("status"),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"data": row_to_dict(obj)}


@router.patch("/api/calendar_events/{event_id}")
def update_calendar_event(event_id: uuid.UUID, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(CalendarEvent, event_id)
    if not obj:
        raise HTTPException(404, "not found")
    apply_fields(obj, payload, {"audit_date", "area_name", "status"})
    db.commit()
    return {"data": row_to_dict(obj)}


@router.delete("/api/calendar_events/{event_id}")
def delete_calendar_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(CalendarEvent, event_id)
    if obj:
        db.delete(obj)
        db.commit()
    return {"ok": True}
