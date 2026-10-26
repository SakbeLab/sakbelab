# Documentación de SakbeLab

- [Especificación del MVP](https://claude.ai/artifact/JwSFizaYnBi8fqtYgExWU5): visión, alcance, arquitectura y hoja de ruta.
- [Formato .sakbe v1](../spec/sakbe-format-v1.md)
- [Imágenes gratuitas e importación](imagenes-gratuitas.md)

## Desarrollo del backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn sakbe.api.main:app --reload
```

La API queda en `http://localhost:8000/api/v1/health` y su documentación interactiva en `http://localhost:8000/docs`.
