# Cómo colaborar con SakbeLab

Gracias por tu interés. SakbeLab crece gracias a su comunidad.

## Formas de ayudar

- **Reportar fallos:** abrí un *Issue* describiendo qué hiciste, qué esperabas y qué pasó. Incluí versión de SakbeLab, hipervisor (VMware o VirtualBox) y sistema operativo del equipo.
- **Proponer ideas:** usá *Discussions* para nuevas funciones antes de programarlas.
- **Plantillas de fabricantes:** agregá plantillas YAML en `templates/`. Nunca subas imágenes.
- **Traducciones:** archivos en `frontend/src/i18n/`.
- **Documentación:** guías, tutoriales y correcciones en `docs/`.
- **Código:** backend, frontend, OVA o herramientas.

## Flujo para enviar cambios

1. Hacé un *fork* del repositorio.
2. Creá una rama con un nombre descriptivo: `feat/consola-vnc`, `fix/import-sakbe`.
3. Hacé commits pequeños y claros.
4. Abrí un *Pull Request* contra `main` explicando qué cambia y por qué.
5. Un mantenedor lo revisa; puede pedir ajustes antes de aprobarlo.

## Convenciones

- **Idioma:** documentación y mensajes de la interfaz en español primero, con su versión en inglés. El código y sus comentarios, en inglés.
- **Python:** formato con `ruff`, tipado con anotaciones, pruebas con `pytest`.
- **Commits:** estilo *Conventional Commits* (`feat:`, `fix:`, `docs:`, `chore:`).

## Reglas importantes

- No subas imágenes, binarios ni licencias de fabricantes, ni enlaces para descargarlos.
- Al contribuir, aceptás que tu aporte se publique bajo la licencia GPLv3 del proyecto.
- Respetá el [código de conducta](CODE_OF_CONDUCT.md).
