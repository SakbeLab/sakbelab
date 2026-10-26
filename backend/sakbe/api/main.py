"""SakbeLab REST API entry point.

API first: the web editor, the CLI and the SDK all go through these endpoints.
"""

import threading
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from sakbe import __version__, engines
from sakbe.api import console, images_api
from sakbe.engines import EngineUnavailable
from sakbe.images import templates
from sakbe.labs import runtime, store
from sakbe.labs.models import Lab, LabCreate, Link, Node, Note, split_endpoint
from sakbe.package import archive
from sakbe.util import CommandError

app = FastAPI(title="SakbeLab API", version=__version__)
app.include_router(images_api.router)
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
_write_lock = threading.RLock()

PLANNED_ENGINES = {
    "qemu": "El motor QEMU llega en la versión 0.2.",
}


def engine_available(engine: str) -> tuple[bool, str]:
    if engine in PLANNED_ENGINES:
        return False, PLANNED_ENGINES[engine]
    if engine in engines.ENGINES:
        return True, ""
    return False, "Motor desconocido."


# ---------------------------------------------------------------- helpers


def _load(name: str) -> Lab:
    try:
        return store.load(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No existe el lab '{name}'") from None


def _node(lab: Lab, name: str) -> Node:
    try:
        return lab.node(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No existe el nodo '{name}'") from None


def _fail(exc: Exception, status: int = 409):
    raise HTTPException(status_code=status, detail=str(exc)) from None


def _template_view(t: templates.Template) -> dict:
    available, reason = engine_available(t.engine)
    return {
        **t.model_dump(),
        "interface_names": t.interfaces.names(),
        "available": available,
        "unavailable_reason": reason,
    }


def _view(lab: Lab) -> dict:
    tpl = templates.load_all()
    states = {n.name: runtime.node_state(lab, n, tpl) for n in lab.nodes}
    data = lab.model_dump()
    for n in data["nodes"]:
        t = tpl.get(n["template"])
        n["state"] = states.get(n["name"], "absent")
        n["icon"] = t.icon if t else "unknown"
        n["category"] = t.category if t else "other"
        n["template_name"] = t.name if t else n["template"]
        n["interfaces"] = t.interfaces.names() if t else []
        n["used_interfaces"] = sorted(lab.used_interfaces(n["name"]))
        n["has_console"] = (
            bool(t)
            and engines.ENGINES.get(t.engine) is not None
            and (engines.ENGINES[t.engine].has_console())
        )
    for link, out in zip(lab.links, data["links"], strict=True):
        a_state = states.get(split_endpoint(link.a)[0])
        b_state = states.get(split_endpoint(link.b)[0])
        out["id"] = link.id(lab.name)
        out["a_up"] = a_state == "running"
        out["b_up"] = b_state == "running"
    values = set(states.values())
    data["state"] = (
        "running"
        if values == {"running"}
        else "stopped"
        if values <= {"absent", "stopped"}
        else "partial"
    )
    return data


def _summary(lab: Lab) -> dict:
    states = runtime.node_states(lab)
    running = sum(1 for s in states.values() if s == "running")
    return {
        "name": lab.name,
        "description": lab.description,
        "nodes": len(lab.nodes),
        "running": running,
    }


def _next_name(lab: Lab, prefix: str) -> str:
    taken = {n.name for n in lab.nodes}
    i = 1
    while f"{prefix}{i}" in taken:
        i += 1
    return f"{prefix}{i}"


def _check_unlocked(item) -> None:
    if item.locked:
        raise HTTPException(
            status_code=423, detail=f"'{getattr(item, 'name', 'La nota')}' está bloqueado."
        )


# ---------------------------------------------------------------- general


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/v1/templates")
def list_templates() -> list[dict]:
    return [_template_view(t) for t in templates.load_all().values()]


class TemplateIn(templates.Template):
    pass


@app.post("/api/v1/templates", status_code=201)
def create_template(payload: TemplateIn, replace: bool = False) -> dict:
    t = templates.Template.model_validate(payload.model_dump())
    with _write_lock:
        if t.id in templates.load_all() and not replace:
            raise HTTPException(status_code=409, detail=f"Ya existe la plantilla '{t.id}'")
        templates.save(t)
    return _template_view(t)


@app.put("/api/v1/templates/{template_id}")
def update_template(template_id: str, payload: TemplateIn) -> dict:
    t = templates.Template.model_validate(payload.model_dump())
    if t.id != template_id:
        raise HTTPException(status_code=422, detail="El id de la plantilla no se puede cambiar")
    with _write_lock:
        templates.save(t)
    return _template_view(t)


@app.delete("/api/v1/templates/{template_id}", status_code=204)
def delete_template(template_id: str) -> None:
    in_use = [
        f"{name}/{n.name}"
        for name in store.list_names()
        for n in store.load(name).nodes
        if n.template == template_id
    ]
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"La plantilla se usa en: {', '.join(in_use[:5])}",
        )
    templates.delete(template_id)


# ---------------------------------------------------------------- labs


@app.get("/api/v1/labs")
def list_labs() -> list[dict]:
    return [_summary(store.load(name)) for name in store.list_names()]


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
        _fail(exc, 422)
    return _save_new(lab, replace)


def _save_new(lab: Lab, replace: bool) -> dict:
    with _write_lock:
        if store.exists(lab.name):
            if not replace:
                raise HTTPException(
                    status_code=409, detail=f"Ya existe un lab llamado '{lab.name}'"
                )
            if runtime.lab_state(store.load(lab.name)) != "stopped":
                raise HTTPException(status_code=409, detail="Apagá el lab antes de reemplazarlo")
        store.save(lab)
    return _view(lab)


@app.get("/api/v1/labs/{name}")
def get_lab(name: str) -> dict:
    return _view(_load(name))


class LabPatch(BaseModel):
    description: str | None = None


@app.patch("/api/v1/labs/{name}")
def patch_lab(name: str, payload: LabPatch) -> dict:
    with _write_lock:
        lab = _load(name)
        if payload.description is not None:
            lab.description = payload.description
        store.save(lab)
    return _view(lab)


@app.get("/api/v1/labs/{name}/yaml")
def export_lab_yaml(name: str):
    lab = _load(name)
    return Response(
        store.lab_to_yaml(lab),
        media_type="text/yaml",
        headers={"Content-Disposition": f'attachment; filename="{name}.yml"'},
    )


@app.get("/api/v1/labs/{name}/sakbe")
def export_lab_sakbe(name: str, author: str = ""):
    lab = _load(name)
    return Response(
        archive.export_lab(lab, author=author),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}.sakbe"'},
    )


@app.post("/api/v1/labs/import", status_code=201)
async def import_lab(request: Request, name: str | None = None, replace: bool = False) -> dict:
    """Import a .sakbe file (ZIP) or a YAML lab sent as the raw request body."""
    blob = await request.body()
    try:
        with _write_lock:
            if blob[:2] == b"PK":
                lab, warnings = archive.import_lab(blob, rename=name, replace=replace)
            else:
                lab = store.lab_from_yaml(blob.decode("utf-8"))
                if name:
                    lab = Lab.model_validate({**lab.model_dump(), "name": name})
                if store.exists(lab.name) and not replace:
                    raise FileExistsError(lab.name)
                store.save(lab)
                warnings = []
    except FileExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un lab llamado '{exc.args[0]}'. Importalo con otro nombre.",
        ) from None
    except (archive.ArchiveError, ValidationError, ValueError, UnicodeDecodeError) as exc:
        _fail(exc, 422)
    return {**_view(lab), "warnings": warnings}


@app.delete("/api/v1/labs/{name}", status_code=204)
def delete_lab(name: str) -> None:
    lab = _load(name)
    runtime.stop(lab)
    for node in lab.nodes:
        runtime.wipe_node(lab, node.name)
    store.delete(name)


@app.post("/api/v1/labs/{name}/start")
def start_lab(name: str) -> dict:
    lab = _load(name)
    try:
        errors = runtime.start(lab)
    except (runtime.LabError, EngineUnavailable) as exc:
        _fail(exc)
    return {**_view(lab), "errors": errors}


@app.post("/api/v1/labs/{name}/stop")
def stop_lab(name: str) -> dict:
    lab = _load(name)
    runtime.stop(lab)
    return _view(lab)


@app.post("/api/v1/labs/{name}/save")
def save_lab_configs(name: str) -> dict:
    with _write_lock:
        lab = _load(name)
        saved = runtime.save_configs(lab)
        store.save(lab)
    return {"saved": saved}


class LockIn(BaseModel):
    locked: bool


@app.post("/api/v1/labs/{name}/lock")
def lock_all(name: str, payload: LockIn) -> dict:
    with _write_lock:
        lab = _load(name)
        for item in [*lab.nodes, *lab.notes]:
            item.locked = payload.locked
        store.save(lab)
    return _view(lab)


# ---------------------------------------------------------------- nodes


class NodeIn(BaseModel):
    template: str
    name: str | None = None
    x: float = 0
    y: float = 0


@app.post("/api/v1/labs/{name}/nodes", status_code=201)
def add_node(name: str, payload: NodeIn) -> dict:
    tpl = templates.load_all()
    if payload.template not in tpl:
        raise HTTPException(status_code=422, detail=f"No existe la plantilla '{payload.template}'")
    with _write_lock:
        lab = _load(name)
        node_name = payload.name or _next_name(lab, tpl[payload.template].name_prefix)
        if node_name in {n.name for n in lab.nodes}:
            raise HTTPException(status_code=409, detail=f"Ya existe un nodo '{node_name}'")
        try:
            node = Node(name=node_name, template=payload.template, x=payload.x, y=payload.y)
        except ValidationError as exc:
            _fail(exc, 422)
        lab.nodes.append(node)
        store.save(lab)
    return _view(lab)


class NodePatch(BaseModel):
    name: str | None = None
    x: float | None = None
    y: float | None = None
    ram: int | None = None
    cpus: int | None = None
    image: str | None = None
    config: str | None = None
    locked: bool | None = None


@app.patch("/api/v1/labs/{name}/nodes/{node_name}")
def patch_node(name: str, node_name: str, payload: NodePatch) -> dict:
    fields = payload.model_dump(exclude_unset=True)
    with _write_lock:
        lab = _load(name)
        node = _node(lab, node_name)
        if node.locked and set(fields) - {"locked"}:
            _check_unlocked(node)
        new_name = fields.pop("name", None)
        for key, value in fields.items():
            setattr(node, key, value)
        if new_name and new_name != node_name:
            _rename(lab, node, new_name)
        try:
            lab = Lab.model_validate(lab.model_dump())
        except ValidationError as exc:
            _fail(exc, 422)
        store.save(lab)
    return _view(lab)


def _rename(lab: Lab, node: Node, new_name: str) -> None:
    if runtime.node_state(lab, node) == "running":
        raise HTTPException(status_code=409, detail="Apagá el nodo antes de renombrarlo")
    if new_name in {n.name for n in lab.nodes}:
        raise HTTPException(status_code=409, detail=f"Ya existe un nodo '{new_name}'")
    touched = lab.links_of(node.name)
    for link in touched:
        runtime.unwire_link(lab, link)
    old = node.name
    node.name = new_name
    for link in touched:
        for attr in ("a", "b"):
            n, iface = split_endpoint(getattr(link, attr))
            if n == old:
                setattr(link, attr, f"{new_name}:{iface}")
    for link in touched:
        runtime.wire_link(lab, link)


@app.delete("/api/v1/labs/{name}/nodes/{node_name}")
def delete_node(name: str, node_name: str) -> dict:
    with _write_lock:
        lab = _load(name)
        node = _node(lab, node_name)
        _check_unlocked(node)
        runtime.stop_node(lab, node_name)
        runtime.wipe_node(lab, node_name)
        for link in lab.links_of(node_name):
            runtime.unwire_link(lab, link)
        lab.links = [link for link in lab.links if link not in lab.links_of(node_name)]
        lab.nodes = [n for n in lab.nodes if n.name != node_name]
        store.save(lab)
    return _view(lab)


@app.post("/api/v1/labs/{name}/nodes/{node_name}/{action}")
def node_action(name: str, node_name: str, action: str) -> dict:
    lab = _load(name)
    _node(lab, node_name)
    try:
        if action == "start":
            runtime.start_node(lab, node_name)
        elif action == "stop":
            runtime.stop_node(lab, node_name)
        elif action == "reload":
            runtime.stop_node(lab, node_name)
            runtime.start_node(lab, node_name)
        else:
            raise HTTPException(status_code=404, detail=f"Acción desconocida '{action}'")
    except (runtime.LabError, EngineUnavailable) as exc:
        _fail(exc)
    except CommandError as exc:
        _fail(exc, 500)
    return _view(lab)


# ---------------------------------------------------------------- links


@app.post("/api/v1/labs/{name}/links", status_code=201)
def add_link(name: str, payload: Link) -> dict:
    with _write_lock:
        lab = _load(name)
        try:
            runtime.validate_link(lab, payload)
            lab = Lab.model_validate(
                {**lab.model_dump(), "links": [*lab.model_dump()["links"], payload.model_dump()]}
            )
        except runtime.LabError as exc:
            _fail(exc, 422)
        except ValidationError as exc:
            _fail(exc, 422)
        store.save(lab)
    try:
        runtime.wire_link(lab, payload)
    except (CommandError, EngineUnavailable) as exc:
        _fail(exc, 500)
    return _view(lab)


@app.delete("/api/v1/labs/{name}/links/{link_id}")
def delete_link(name: str, link_id: str) -> dict:
    with _write_lock:
        lab = _load(name)
        try:
            link = lab.link(link_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="No existe ese enlace") from None
        runtime.unwire_link(lab, link)
        lab.links = [lk for lk in lab.links if lk.id(lab.name) != link_id]
        store.save(lab)
    return _view(lab)


# ---------------------------------------------------------------- notes


class NoteIn(BaseModel):
    text: str = ""
    x: float = 0
    y: float = 0


class NotePatch(BaseModel):
    text: str | None = None
    x: float | None = None
    y: float | None = None
    locked: bool | None = None


@app.post("/api/v1/labs/{name}/notes", status_code=201)
def add_note(name: str, payload: NoteIn) -> dict:
    with _write_lock:
        lab = _load(name)
        lab.notes.append(Note(id=uuid.uuid4().hex[:8], **payload.model_dump()))
        store.save(lab)
    return _view(lab)


def _note(lab: Lab, note_id: str) -> Note:
    for note in lab.notes:
        if note.id == note_id:
            return note
    raise HTTPException(status_code=404, detail="No existe esa nota")


@app.patch("/api/v1/labs/{name}/notes/{note_id}")
def patch_note(name: str, note_id: str, payload: NotePatch) -> dict:
    fields = payload.model_dump(exclude_unset=True)
    with _write_lock:
        lab = _load(name)
        note = _note(lab, note_id)
        if note.locked and set(fields) - {"locked"}:
            _check_unlocked(note)
        for key, value in fields.items():
            setattr(note, key, value)
        store.save(lab)
    return _view(lab)


@app.delete("/api/v1/labs/{name}/notes/{note_id}")
def delete_note(name: str, note_id: str) -> dict:
    with _write_lock:
        lab = _load(name)
        _check_unlocked(_note(lab, note_id))
        lab.notes = [n for n in lab.notes if n.id != note_id]
        store.save(lab)
    return _view(lab)


# ---------------------------------------------------------------- console


@app.websocket("/api/v1/labs/{name}/nodes/{node}/console")
async def node_console(ws: WebSocket, name: str, node: str) -> None:
    await ws.accept()
    try:
        command = runtime.console_command(store.load(name), node)
    except (KeyError, EngineUnavailable, runtime.LabError) as exc:
        await ws.send_text(f"\r\nNo se puede abrir la consola: {exc}\r\n")
        await ws.close()
        return
    await console.bridge(ws, command)


# ---------------------------------------------------------------- web app


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    return FileResponse(WEB_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/console/{lab}/{node}", include_in_schema=False)
def console_page(lab: str, node: str):
    return FileResponse(WEB_DIR / "index.html")


app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets", check_dir=False), name="assets")
