from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import OwnerDirectory
from utils import apply_fields, row_to_dict

router = APIRouter()


@router.get("/api/owners_directory")
def list_owners(db: Session = Depends(get_db)):
    rows = db.query(OwnerDirectory).order_by(OwnerDirectory.area_id.asc()).all()
    return {"data": [row_to_dict(r) for r in rows]}


@router.post("/api/owners_directory")
def create_owner(payload: dict = Body(...), db: Session = Depends(get_db)):
    area_id = payload.get("area_id")
    if not area_id:
        raise HTTPException(400, "area_id es requerido")
    obj = OwnerDirectory(
        area_id=area_id,
        owner_name=payload.get("owner_name"),
        department=payload.get("department"),
    )
    db.add(obj)
    db.commit()
    return {"data": row_to_dict(obj)}


@router.patch("/api/owners_directory/{area_id}")
def update_owner(area_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(OwnerDirectory, area_id)
    if not obj:
        raise HTTPException(404, "not found")
    apply_fields(obj, payload, {"owner_name", "department"})
    db.commit()
    return {"data": row_to_dict(obj)}


@router.delete("/api/owners_directory/{area_id}")
def delete_owner(area_id: str, db: Session = Depends(get_db)):
    obj = db.get(OwnerDirectory, area_id)
    if obj:
        db.delete(obj)
        db.commit()
    return {"ok": True}
