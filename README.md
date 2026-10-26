# SakbeLab

**Emulador de redes open source, listo para usar en una OVA.**
*Open source network emulator, ready to run as an OVA.* ([English below](#english))

Los sakbé eran las calzadas blancas que conectaban las ciudades mayas. SakbeLab conecta tus equipos virtuales.

> Estado: versión 0.1 en desarrollo. Editor web estilo GNS3, routers FRR, switch Ethernet integrado, Cisco IOL, archivos `.sakbe` y SDK de Python. Ver la [documentación](docs/README.md).

## Qué es

SakbeLab es una plataforma de emulación de redes pensada para estudiantes e instructores:

- **Se instala importando una OVA** en VMware o VirtualBox. Nada más.
- **Se usa desde el navegador:** editor de topologías, consolas web y gestión de labs.
- **Cascarón vacío y liviano:** no trae imágenes ni labs precargados. Cada usuario carga las suyas.
- **Corre imágenes QCOW2, Cisco IOL y Docker**, con plantillas configurables por fabricante.
- **Labs portables:** cada laboratorio se exporta en un archivo `.sakbe` que se comparte e importa con un clic.
- **Labs como código:** los labs también se crean desde YAML o desde Python con el SDK `sakbe`.

## Ejemplo: un lab en Python

```python
from sakbe import Lab

lab = Lab("ospf-area0", server="http://192.168.56.101")

r1 = lab.node("R1", template="frr")
r2 = lab.node("R2", template="frr")
lab.link(r1["eth1"], r2["eth1"])

lab.deploy()
lab.export("ospf-area0.sakbe")
```

## Imágenes de fabricantes

SakbeLab **no incluye ni distribuye** imágenes de Cisco, Fortinet ni de ningún otro fabricante. Cada usuario es responsable de obtener sus imágenes con la licencia correspondiente.

## Estructura del repositorio

| Carpeta | Contenido |
| --- | --- |
| `backend/` | API y motor de emulación (Python, FastAPI) |
| `frontend/` | Interfaz web (React, TypeScript) |
| `templates/` | Plantillas de nodos por fabricante, sin imágenes |
| `ova/` | Construcción de la OVA con Packer |
| `tools/` | Verificador de requisitos para Windows y utilidades |
| `spec/` | Especificación abierta del formato `.sakbe` |
| `docs/` | Documentación de usuario y desarrollo |

## Cómo colaborar

Toda ayuda suma: código, plantillas de fabricantes, traducciones, documentación o reportes de fallos. Leé [CONTRIBUTING.md](CONTRIBUTING.md) para empezar.

## Licencia

SakbeLab es software libre bajo la licencia [GNU GPL v3](LICENSE). El nombre y el logo de SakbeLab son marcas del proyecto.

Sitio: [sakbelab.dev](https://sakbelab.dev)

---

## English

SakbeLab is an open source network emulation platform built for students and instructors.

- **Install by importing an OVA** into VMware or VirtualBox.
- **Use it from your browser:** topology editor, web consoles and lab management.
- **Empty and lightweight:** no bundled images or labs. Users bring their own.
- **Runs QCOW2, Cisco IOL and Docker images** with configurable per-vendor templates.
- **Portable labs:** export any lab as a `.sakbe` file and share it.
- **Labs as code:** define labs in YAML or Python with the `sakbe` SDK.

SakbeLab does **not** ship or distribute vendor images. Users must obtain properly licensed images.

Status: early development (Phase 0, proof of concept). Contributions are welcome, see [CONTRIBUTING.md](CONTRIBUTING.md).

License: [GNU GPL v3](LICENSE).
