"""Image upload and listing. Uploads stream to disk, so multi-GB files are fine."""

import hashlib
import uuid

from fastapi import APIRouter, HTTPException, Request

from sakbe.images import store as images
from sakbe.util import CommandError

router = APIRouter(prefix="/api/v1/images", tags=["images"])


@router.get("")
def list_images() -> list[dict]:
    return images.list_all()


@router.get("/docker-local")
def list_local_docker_images() -> list[str]:
    return images.local_docker_images()


@router.put("/{kind}/{filename}", status_code=201)
async def upload_image(kind: str, filename: str, request: Request) -> dict:
    try:
        images.path_for(kind, filename)
    except images.ImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    part = images.kind_dir(kind) / f".{uuid.uuid4().hex}.part"
    digest = hashlib.sha256()
    size = 0
    try:
        with part.open("wb") as fh:
            async for chunk in request.stream():
                digest.update(chunk)
                fh.write(chunk)
                size += len(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="El archivo está vacío.")
        return images.finalize(kind, filename, part, digest.hexdigest())
    except CommandError as exc:
        raise HTTPException(status_code=422, detail=f"No se pudo cargar la imagen: {exc}") from None
    finally:
        part.unlink(missing_ok=True)


@router.delete("/{kind}/{name}", status_code=204)
def delete_image(kind: str, name: str) -> None:
    try:
        images.delete(kind, name)
    except images.ImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
