import asyncio
import json
import random
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import GembaEvent, GembaLiveAction, GembaParticipant
from utils import apply_fields, row_to_dict

router = APIRouter()


def _new_pin(db: Session) -> str:
    for _ in range(20):
        pin = f"{random.randint(0, 9999):04d}"
        if not db.query(GembaEvent).filter(GembaEvent.pin_code == pin).first():
            return pin
    raise HTTPException(500, "no se pudo generar un PIN unico, intenta de nuevo")


# --- gemba_events ---


@router.post("/api/gemba_events")
def create_gemba_event(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = GembaEvent(
        event_date=payload.get("event_date"),
        shift=payload.get("shift"),
        areas=payload.get("areas"),
        admin_name=payload.get("admin_name"),
        pin_code=_new_pin(db),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"data": row_to_dict(obj)}


@router.patch("/api/gemba_events/{event_id}")
def update_gemba_event(event_id: uuid.UUID, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(GembaEvent, event_id)
    if not obj:
        raise HTTPException(404, "not found")
    apply_fields(obj, payload, {"status"})
    db.commit()
    return {"data": row_to_dict(obj)}


@router.get("/api/gemba_events/by_pin/{pin}")
def get_gemba_event_by_pin(pin: str, db: Session = Depends(get_db)):
    obj = (
        db.query(GembaEvent)
        .filter(GembaEvent.pin_code == pin, GembaEvent.status != "completed")
        .first()
    )
    return {"data": row_to_dict(obj) if obj else None}


@router.get("/api/gemba_events/{event_id}")
def get_gemba_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(GembaEvent, event_id)
    if not obj:
        raise HTTPException(404, "not found")
    return {"data": row_to_dict(obj)}


# --- gemba_participants ---


@router.get("/api/gemba_participants")
def list_gemba_participants(event_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    rows = db.query(GembaParticipant).filter(GembaParticipant.event_id == event_id).all()
    return {"data": [row_to_dict(r) for r in rows]}


@router.post("/api/gemba_participants")
def create_gemba_participant(payload: dict = Body(...), db: Session = Depends(get_db)):
    event_id = payload.get("event_id")
    if not event_id:
        raise HTTPException(400, "event_id es requerido")
    obj = GembaParticipant(
        event_id=uuid.UUID(str(event_id)),
        participant_name=payload.get("participant_name"),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"data": row_to_dict(obj)}


@router.get("/api/gemba_participants/{participant_id}")
def get_gemba_participant(participant_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(GembaParticipant, participant_id)
    if not obj:
        raise HTTPException(404, "not found")
    return {"data": row_to_dict(obj)}


@router.patch("/api/gemba_participants/{participant_id}")
def update_gemba_participant(participant_id: uuid.UUID, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(GembaParticipant, participant_id)
    if not obj:
        raise HTTPException(404, "not found")
    apply_fields(obj, payload, {"assigned_section"})
    db.commit()
    return {"data": row_to_dict(obj)}


# --- gemba_live_actions ---


@router.get("/api/gemba_live_actions")
def list_gemba_live_actions(event_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    rows = db.query(GembaLiveAction).filter(GembaLiveAction.event_id == event_id).all()
    return {"data": [row_to_dict(r) for r in rows]}


@router.post("/api/gemba_live_actions")
def create_gemba_live_action(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = GembaLiveAction(
        event_id=uuid.UUID(str(payload.get("event_id"))),
        participant_id=uuid.UUID(str(payload.get("participant_id"))),
        section=payload.get("section"),
        question=payload.get("question"),
        action_text=payload.get("action_text"),
        owner=payload.get("owner"),
        due_date=payload.get("due_date"),
        priority=payload.get("priority"),
        photo_base64=payload.get("photo_base64"),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"data": row_to_dict(obj)}


# --- SSE: reemplazo de Supabase Realtime ---
# Reemplaza los 2 canales `postgres_changes` del index.html original. El
# polling manual que ya existia en el frontend como respaldo se deja intacto,
# esto es solo la version "live" con menor latencia.


async def _sse_admin_stream(event_id: uuid.UUID):
    last_snapshot = None
    try:
        while True:
            db = SessionLocal()
            try:
                rows = db.query(GembaParticipant).filter(GembaParticipant.event_id == event_id).all()
                snapshot = tuple((str(r.id), r.assigned_section) for r in rows)
                if snapshot != last_snapshot:
                    last_snapshot = snapshot
                    data = [row_to_dict(r) for r in rows]
                    yield f"event: participants\ndata: {json.dumps(data)}\n\n"
                else:
                    yield "event: ping\ndata: ok\n\n"
            finally:
                db.close()
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        return


@router.get("/api/gemba_events/{event_id}/stream/admin")
async def stream_admin(event_id: uuid.UUID):
    return StreamingResponse(_sse_admin_stream(event_id), media_type="text/event-stream")


async def _sse_participant_stream(event_id: uuid.UUID, participant_id: uuid.UUID):
    last_status = None
    last_section = None
    try:
        while True:
            db = SessionLocal()
            try:
                event = db.get(GembaEvent, event_id)
                participant = db.get(GembaParticipant, participant_id)
                if event and event.status != last_status:
                    last_status = event.status
                    yield f"event: event_status\ndata: {json.dumps({'status': event.status})}\n\n"
                elif participant and participant.assigned_section != last_section:
                    last_section = participant.assigned_section
                    yield f"event: participant_update\ndata: {json.dumps({'assigned_section': participant.assigned_section})}\n\n"
                else:
                    yield "event: ping\ndata: ok\n\n"
            finally:
                db.close()
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        return


@router.get("/api/gemba_events/{event_id}/stream/participant")
async def stream_participant(event_id: uuid.UUID, participant_id: uuid.UUID = Query(...)):
    return StreamingResponse(
        _sse_participant_stream(event_id, participant_id), media_type="text/event-stream"
    )
