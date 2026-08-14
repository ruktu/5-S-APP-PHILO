from fastapi import FastAPI

import models  # noqa: F401 - registra los modelos en Base antes de create_all
from database import Base, engine
from routers import actions, calendar_events, evidence, gemba, layout_coords, owners_directory, perfiles

app = FastAPI(title="LeanView 5'S API")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"ok": True}


app.include_router(actions.router)
app.include_router(layout_coords.router)
app.include_router(owners_directory.router)
app.include_router(perfiles.router)
app.include_router(calendar_events.router)
app.include_router(gemba.router)
app.include_router(evidence.router)
