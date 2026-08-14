import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Perfil
from utils import apply_fields, row_to_dict

router = APIRouter()


@router.get("/api/perfiles/{perfil_id}")
def get_perfil(perfil_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(Perfil, perfil_id)
    if not obj:
        raise HTTPException(404, "not found")
    return {"data": row_to_dict(obj)}


@router.patch("/api/perfiles/{perfil_id}")
def update_perfil(perfil_id: uuid.UUID, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(Perfil, perfil_id)
    if not obj:
        raise HTTPException(404, "not found")
    apply_fields(obj, payload, {"email", "rol", "primer_ingreso", "area"})
    db.commit()
    return {"data": row_to_dict(obj)}
