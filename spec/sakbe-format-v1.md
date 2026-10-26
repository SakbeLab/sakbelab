# Formato de archivo `.sakbe`, versión 1 (borrador)

Un archivo `.sakbe` es un ZIP que contiene un laboratorio completo, excepto las imágenes de fabricante.

## Estructura

```
mi-lab.sakbe
├── manifest.json     metadatos del lab y lista de imágenes requeridas
├── topology.yml      nodos, enlaces, posiciones y notas (mismo YAML de labs como código)
├── configs/          configuración de cada equipo (R1.cfg, SW1.cfg...)
├── templates/        plantillas de nodo usadas, sin imágenes
├── docs/             opcional: enunciado del lab
└── images/           opcional y explícito: solo imágenes de licencia libre
```

## manifest.json

```json
{
  "format": "sakbe",
  "version": 1,
  "name": "OSPF multiárea",
  "author": "Victor Rodas",
  "created": "2026-10-25",
  "requires": [
    {"template": "cisco-iol-l3", "sha256": "a3f9...", "hint": "IOL L3 15.x"}
  ]
}
```

## topology.yml

```yaml
name: ospf-area0
nodes:
  R1: {template: cisco-iol-l3, ram: 512, config: configs/R1.cfg, x: 100, y: 200}
  R2: {template: cisco-iol-l3, ram: 512, config: configs/R2.cfg, x: 300, y: 200}
links:
  - [R1:Ethernet0/0, R2:Ethernet0/0]
```

## Reglas de importación

1. Se valida `format` y `version`.
2. Por cada entrada de `requires` se busca la plantilla instalada y se compara su SHA256.
3. Si falta una imagen, el lab se abre en modo solo lectura y se indica cuál falta.
4. Si la plantilla existe pero la huella no coincide, se avisa y se permite continuar.

Esta especificación es abierta: cualquier herramienta puede leer y escribir archivos `.sakbe`.
