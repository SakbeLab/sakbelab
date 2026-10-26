"""SakbeLab REST API entry point.

Phase 0: health check and a minimal in-memory lab model. Every feature of the
web UI, the CLI and the SDK must go through this API ("API first").
"""

from fastapi import FastAPI, HTTPException

from sakbe import __version__
from sakbe.labs.models import Lab, LabCreate

app = FastAPI(title="SakbeLab API", version=__version__)

_labs: dict[str, Lab] = {}


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/v1/labs")
def list_labs() -> list[Lab]:
    return list(_labs.values())


@app.post("/api/v1/labs", status_code=201)
def create_lab(payload: LabCreate) -> Lab:
    if payload.name in _labs:
        raise HTTPException(status_code=409, detail="Lab already exists")
    lab = Lab(**payload.model_dump())
    _labs[lab.name] = lab
    return lab


@app.get("/api/v1/labs/{name}")
def get_lab(name: str) -> Lab:
    if name not in _labs:
        raise HTTPException(status_code=404, detail="Lab not found")
    return _labs[name]
