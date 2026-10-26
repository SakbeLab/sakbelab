"""`sakbe` command line interface. It talks to the SakbeLab API (API first).

sakbe [--server URL] list
sakbe deploy lab.yml            crear (o reemplazar) y encender
sakbe start|stop LAB [NODO]
sakbe destroy LAB [--delete]
sakbe export LAB [-o archivo.sakbe|.yml]
sakbe import archivo.sakbe|.yml [--name NUEVO]
sakbe templates | images
sakbe upload imagen.qcow2|.bin|.tar
"""

import argparse
import os
import sys
from pathlib import Path

from sakbe import __version__
from sakbe.client import DEFAULT_SERVER, Client, SakbeError, quote


def _print_lab(lab: dict) -> None:
    print(f"{lab['name']}: {lab.get('state', '')}")
    for n in lab.get("nodes", []):
        print(f"  {n['name']:<14} {n['template']:<18} {n['state']}")
    for e in lab.get("errors", []) or []:
        print(f"  ! {e}")
    for w in lab.get("warnings", []) or []:
        print(f"  ! {w}")


def _kind(path: Path) -> str | None:
    name = path.name.lower()
    if name.endswith((".qcow2", ".img", ".vmdk", ".iso")):
        return "qemu"
    if name.endswith((".tar", ".tar.gz", ".tgz")):
        return "docker"
    if name.endswith((".bin", ".iol")) or "." not in name:
        return "iol"
    return None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="sakbe", description="SakbeLab: emulador de redes")
    parser.add_argument("--version", action="version", version=f"sakbe {__version__}")
    parser.add_argument(
        "--server",
        default=os.environ.get("SAKBE_SERVER", DEFAULT_SERVER),
        help=f"dirección de SakbeLab (default {DEFAULT_SERVER} o $SAKBE_SERVER)",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="listar labs")
    p = sub.add_parser("deploy", help="crear un lab desde YAML y encenderlo")
    p.add_argument("file")
    p.add_argument("--no-start", action="store_true", help="crear sin encender")
    for cmd, text in (("start", "encender un lab o un nodo"), ("stop", "apagar un lab o un nodo")):
        p = sub.add_parser(cmd, help=text)
        p.add_argument("lab")
        p.add_argument("node", nargs="?")
    p = sub.add_parser("destroy", help="apagar un lab (y opcionalmente borrarlo)")
    p.add_argument("lab")
    p.add_argument("--delete", action="store_true", help="además, borrar su definición")
    p = sub.add_parser("export", help="exportar un lab a .sakbe o .yml")
    p.add_argument("lab")
    p.add_argument("-o", "--output", help="archivo de salida (default <lab>.sakbe)")
    p.add_argument(
        "--save", action="store_true", help="guardar antes la configuración de los equipos"
    )
    p.add_argument("--author", default="")
    p = sub.add_parser("import", help="importar un .sakbe o .yml")
    p.add_argument("file")
    p.add_argument("--name", help="importar con otro nombre")
    sub.add_parser("templates", help="listar plantillas")
    sub.add_parser("images", help="listar imágenes")
    p = sub.add_parser("upload", help="subir una imagen (QCOW2, IOL o tar de Docker)")
    p.add_argument("file")
    args = parser.parse_args(argv)
    c = Client(args.server)

    try:
        run(args, c, parser)
    except SakbeError as exc:
        sys.exit(f"Error: {exc}")
    except OSError as exc:
        sys.exit(f"Error: {exc}")


def run(args, c: Client, parser) -> None:
    cmd = args.command
    if cmd == "list":
        labs = c.get("/labs")
        if not labs:
            print("No hay labs.")
        for lab in labs:
            print(
                f"{lab['name']:<24} {lab['nodes']} equipos, {lab['running']} encendidos  {lab['description']}"
            )
    elif cmd == "deploy":
        from sakbe.sdk import Lab

        lab = Lab.from_yaml(args.file, server=args.server)
        errors = lab.deploy(start=not args.no_start)
        _print_lab({**c.get(f"/labs/{quote(lab.name)}"), "errors": errors})
    elif cmd in ("start", "stop"):
        path = f"/labs/{quote(args.lab)}"
        if args.node:
            path += f"/nodes/{quote(args.node)}"
        _print_lab(c.post(f"{path}/{cmd}"))
    elif cmd == "destroy":
        if args.delete:
            c.delete(f"/labs/{quote(args.lab)}")
            print(f"Lab '{args.lab}' apagado y eliminado.")
        else:
            _print_lab(c.post(f"/labs/{quote(args.lab)}/stop"))
    elif cmd == "export":
        if args.save:
            c.post(f"/labs/{quote(args.lab)}/save")
        out = Path(args.output or f"{args.lab}.sakbe")
        kind = "yaml" if out.suffix in (".yml", ".yaml") else "sakbe"
        data = c.get(f"/labs/{quote(args.lab)}/{kind}", params={"author": args.author or None})
        out.write_bytes(data if isinstance(data, bytes) else str(data).encode())
        print(f"Exportado a {out}")
    elif cmd == "import":
        blob = Path(args.file).read_bytes()
        lab = c.request(
            "POST",
            "/labs/import",
            raw=blob,
            content_type="application/octet-stream",
            params={"name": args.name},
        )
        _print_lab(lab)
    elif cmd == "templates":
        for t in c.get("/templates"):
            state = "" if t["available"] else f"  ({t['unavailable_reason']})"
            print(
                f"{t['id']:<22} {t['name']:<22} {t['engine']:<7} {len(t['interface_names'])} interfaces{state}"
            )
    elif cmd == "images":
        for i in c.get("/images"):
            sha = (i["sha256"] or "")[:12]
            print(f"{i['kind']:<7} {i['reference'] or i['name']:<50} {sha}")
    elif cmd == "upload":
        path = Path(args.file)
        kind = _kind(path)
        if not kind:
            sys.exit("Formato no reconocido: use .qcow2, .img, .vmdk, .iso, .bin o .tar")
        with path.open("rb") as fh:
            info = c.request(
                "PUT",
                f"/images/{kind}/{quote(path.name)}",
                raw=fh,
                content_type="application/octet-stream",
            )
        print(f"Cargada {info['name']} ({kind}), SHA256 {info['sha256']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
