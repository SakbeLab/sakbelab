"""`sakbe` command line interface. It talks to the SakbeLab API (API first)."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from sakbe import __version__

DEFAULT_SERVER = os.environ.get("SAKBE_SERVER", "http://localhost")


def _call(
    server: str,
    method: str,
    path: str,
    body: bytes | None = None,
    content_type: str = "application/json",
):
    req = urllib.request.Request(server.rstrip("/") + "/api/v1" + path, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=300) as res:
            raw = res.read()
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read()).get("detail")
        except (ValueError, AttributeError):
            detail = exc.reason
        sys.exit(f"Error: {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"No se pudo conectar con {server}: {exc.reason}")
    return json.loads(raw) if raw else None


def _print_lab(lab: dict) -> None:
    print(f"{lab['name']}: {lab['state']}")
    for n in lab["nodes"]:
        print(f"  {n['name']:<12} {n['template']:<14} {n['state']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="sakbe", description="SakbeLab CLI")
    parser.add_argument("--version", action="version", version=f"sakbe {__version__}")
    parser.add_argument("--server", default=DEFAULT_SERVER, help=f"API (default {DEFAULT_SERVER})")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("deploy", help="Crear un lab desde YAML y encenderlo")
    p.add_argument("file")
    p.add_argument("--replace", action="store_true", help="Reemplazar si ya existe (apagado)")
    p = sub.add_parser("destroy", help="Apagar un lab")
    p.add_argument("name")
    p.add_argument("--delete", action="store_true", help="Además, borrar su definición")
    sub.add_parser("list", help="Listar labs")
    p = sub.add_parser("export", help="Guardar la configuración actual y exportar el lab a YAML")
    p.add_argument("name")
    p.add_argument("-o", "--output", help="Archivo de salida (default <name>.yml)")
    args = parser.parse_args()
    s = args.server

    if args.command == "deploy":
        with open(args.file, "rb") as fh:
            text = fh.read()
        query = "?replace=true" if args.replace else ""
        lab = _call(s, "POST", f"/labs/yaml{query}", text, "text/plain")
        print(f"Lab '{lab['name']}' creado. Encendiendo...")
        _print_lab(_call(s, "POST", f"/labs/{urllib.parse.quote(lab['name'])}/start"))
    elif args.command == "destroy":
        name = urllib.parse.quote(args.name)
        if args.delete:
            _call(s, "DELETE", f"/labs/{name}")
            print(f"Lab '{args.name}' apagado y eliminado.")
        else:
            _print_lab(_call(s, "POST", f"/labs/{name}/stop"))
    elif args.command == "list":
        labs = _call(s, "GET", "/labs")
        if not labs:
            print("No hay labs.")
        for lab in labs:
            _print_lab(lab)
    elif args.command == "export":
        name = urllib.parse.quote(args.name)
        _call(s, "POST", f"/labs/{name}/save")
        url = s.rstrip("/") + f"/api/v1/labs/{name}/yaml"
        out = args.output or f"{args.name}.yml"
        with urllib.request.urlopen(url) as res, open(out, "wb") as fh:
            fh.write(res.read())
        print(f"Exportado a {out}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
