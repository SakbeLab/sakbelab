# Documentación de SakbeLab

- [Especificación del MVP](https://claude.ai/artifact/JwSFizaYnBi8fqtYgExWU5): visión, alcance, arquitectura y hoja de ruta.
- [Prueba de la Fase 0](fase0.md): instalación en una VM y primer lab
- [Actualizar SakbeLab](actualizar.md)
- [Construir la OVA](../ova/README.md)
- [Formato .sakbe v1](../spec/sakbe-format-v1.md)
- [Imágenes gratuitas e importación](imagenes-gratuitas.md)
- [Cisco IOL](iol.md)
- [Imágenes QEMU (QCOW2)](qemu.md)
- [Labs como código: SDK de Python, YAML y CLI](labs-como-codigo.md)

## Desarrollo del backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
sudo SAKBE_DATA=/tmp/sakbe uvicorn sakbe.api.main:app --reload   # root: crea bridges y contenedores
```

La API queda en `http://localhost:8000/api/v1/health` y su documentación interactiva en `http://localhost:8000/docs`.
