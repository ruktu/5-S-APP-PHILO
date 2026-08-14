from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import LayoutCoord
from utils import row_to_dict

router = APIRouter()

_ALLOWED_FIELDS = {"map", "type", "name", "x", "y", "width", "height"}


@router.get("/api/layout_coords")
def list_layout_coords(db: Session = Depends(get_db)):
    rows = db.query(LayoutCoord).all()
    return {"data": [row_to_dict(r) for r in rows]}


@router.delete("/api/layout_coords")
def delete_all_layout_coords(db: Session = Depends(get_db)):
    db.query(LayoutCoord).delete()
    db.commit()
    return {"ok": True}


@router.post("/api/layout_coords")
def bulk_insert_layout_coords(payload: dict = Body(...), db: Session = Depends(get_db)):
    rows = payload.get("rows", [])
    for row in rows:
        filtered = {k: v for k, v in row.items() if k in _ALLOWED_FIELDS}
        db.add(LayoutCoord(**filtered))
    db.commit()
    return {"ok": True, "count": len(rows)}
