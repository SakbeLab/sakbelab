"""SakbeLab REST API entry point.

API first: the web UI, the CLI and the SDK all go through these endpoints.
"""

from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from sakbe import __version__, settings
from sakbe.api import console
from sakbe.engines import EngineUnavailable
from sakbe.images import templates
from sakbe.labs import runtime, store
from sakbe.labs.models import Lab, LabCreate
from sakbe.util import CommandError

app = FastAPI(title="SakbeLab API", version=__version__)
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def _load(name: str) -> Lab:
    try:
        return store.load(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No existe el lab '{name}'") from None


def _view(lab: Lab) -> dict:
    states = runtime.node_states(lab)
    data = lab.model_dump()
    for n in data["nodes"]:
        n["state"] = states.get(n["name"], "absent")
    values = set(states.values())
    data["state"] = (
        "running" if values == {"running"} else ("stopped" if values <= {"absent"} else "partial")
    )
    return data


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/v1/templates")
def list_templates() -> list[dict]:
    return [
        {**t.model_dump(), "interface_names": t.interfaces.names()}
        for t in templates.load_all().values()
    ]


@app.get("/api/v1/labs")
def list_labs() -> list[dict]:
    return [_view(store.load(name)) for name in store.list_names()]


@app.post("/api/v1/labs", status_code=201)
def create_lab(payload: LabCreate, replace: bool = False) -> dict:
    lab = Lab(**payload.model_dump())
    return _save_new(lab, replace)


@app.post("/api/v1/labs/yaml", status_code=201)
def create_lab_from_yaml(
    text: str = Body(..., media_type="text/plain"), replace: bool = False
) -> dict:
    try:
        lab = store.lab_from_yaml(text)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _save_new(lab, replace)


def _save_new(lab: Lab, replace: bool) -> dict:
    if store.exists(lab.name):
        if not replace:
            raise HTTPException(status_code=409, detail=f"Ya existe un lab llamado '{lab.name}'")
        if runtime.lab_state(store.load(lab.name)) != "stopped":
            raise HTTPException(status_code=409, detail="Apagá el lab antes de reemplazarlo")
    store.save(lab)
    return _view(lab)


@app.get("/api/v1/labs/{name}")
def get_lab(name: str) -> dict:
    return _view(_load(name))


@app.get("/api/v1/labs/{name}/yaml", response_class=FileResponse)
def export_lab_yaml(name: str):
    _load(name)
    path = settings.labs_dir() / f"{name}.yml"
    return FileResponse(path, media_type="text/yaml", filename=f"{name}.yml")


@app.delete("/api/v1/labs/{name}", status_code=204)
def delete_lab(name: str) -> None:
    lab = _load(name)
    runtime.stop(lab)
    store.delete(name)


@app.post("/api/v1/labs/{name}/start")
def start_lab(name: str) -> dict:
    lab = _load(name)
    try:
        runtime.start(lab)
    except (runtime.LabError, EngineUnavailable) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except CommandError as exc:
        raise HTTPException(status_code=500, detail=f"Error al encender el lab: {exc}") from None
    return _view(lab)


@app.post("/api/v1/labs/{name}/stop")
def stop_lab(name: str) -> dict:
    lab = _load(name)
    runtime.stop(lab)
    return _view(lab)


@app.post("/api/v1/labs/{name}/save")
def save_lab_configs(name: str) -> dict:
    lab = _load(name)
    saved = runtime.save_configs(lab)
    store.save(lab)
    return {"saved": saved}


@app.websocket("/api/v1/labs/{name}/nodes/{node}/console")
async def node_console(ws: WebSocket, name: str, node: str) -> None:
    await ws.accept()
    try:
        command = runtime.console_command(store.load(name), node)
    except (KeyError, EngineUnavailable) as exc:
        await ws.send_text(f"\r\nNo se puede abrir la consola: {exc}\r\n")
        await ws.close()
        return
    await console.bridge(ws, command)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
