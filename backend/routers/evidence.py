import os
import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter()

UPLOAD_DIR = "/app/instance/uploads/evidence"
MAX_BYTES = 5 * 1024 * 1024  # 5MB, generoso para un JPEG 800x800 ya comprimido en el navegador
_SAFE = re.compile(r"[^A-Za-z0-9_-]")


@router.post("/api/evidence")
async def upload_evidence(
    file: UploadFile = File(...),
    audit_id: str = Form(...),
    question_id: str = Form(...),
):
    ext = (file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg").lower()
    ext = _SAFE.sub("", ext) or "jpg"
    safe_audit_id = _SAFE.sub("", audit_id)
    safe_question_id = _SAFE.sub("", question_id)
    filename = f"{safe_audit_id}_{safe_question_id}.{ext}"

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(UPLOAD_DIR, filename)

    contents = await file.read(MAX_BYTES + 1)
    if len(contents) > MAX_BYTES:
        raise HTTPException(413, "archivo demasiado grande")

    with open(dest_path, "wb") as f:
        f.write(contents)

    return {"url": f"/evidence/{filename}"}
