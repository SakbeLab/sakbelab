# Formato de archivo `.sakbe`, versión 1

Un archivo `.sakbe` es un ZIP que contiene un laboratorio completo, excepto las imágenes de fabricante.

## Estructura

```
mi-lab.sakbe
├── manifest.json     metadatos del lab y lista de imágenes requeridas
├── topology.yml      nodos, enlaces, posiciones y notas (mismo YAML de labs como código)
├── configs/          configuración inicial de cada equipo (R1.cfg, SW1.cfg...)
└── templates/        plantillas de nodo usadas, sin imágenes
```

## manifest.json

```json
{
  "format": "sakbe",
  "version": 1,
  "name": "ospf-area0",
  "description": "OSPF en área 0",
  "author": "Victor Rodas",
  "created": "2026-10-26",
  "generator": "SakbeLab 0.1.0",
  "requires": [
    {
      "template": "cisco-iol-l3",
      "engine": "iol",
      "image": "i86bi-linux-l3-adventerprisek9-15.5.2T.bin",
      "sha256": "a3f9...",
      "hint": "Cisco IOL L3"
    }
  ]
}
```

`sha256` puede ser `null` cuando la imagen se copió al servidor sin calcular su huella.

## topology.yml

```yaml
name: ospf-area0
description: OSPF en área 0
nodes:
  R1: {template: cisco-iol-l3, x: 100, y: 200, config: configs/R1.cfg}
  R2: {template: cisco-iol-l3, x: 300, y: 200, config: configs/R2.cfg}
  SW1: {template: ethernet-switch, x: 200, y: 340}
links:
  - [R1:Ethernet0/0, SW1:e0]
  - [R2:Ethernet0/0, SW1:e1]
notes:
  - {id: a1b2c3d4, text: "Área 0", x: 80, y: 120}
```

Dentro del archivo, `config` apunta a un archivo de `configs/`. En el YAML de labs como código, `config` contiene el texto directamente.

## Reglas de importación

1. Se valida `format` y `version`. Una versión mayor a la soportada se rechaza con un mensaje para actualizar SakbeLab.
2. Se rechazan rutas absolutas o con `..`, más de 2000 archivos o más de 50 MB descomprimidos.
3. Cada plantilla de `templates/` que no esté instalada se instala. Las ya instaladas no se reemplazan.
4. Por cada entrada de `requires` se verifica la imagen: si falta, o si su SHA256 no coincide, se avisa al usuario. El lab se importa igual; los equipos sin imagen no arrancan hasta que se cargue.
5. Si ya existe un lab con el mismo nombre, se pide otro nombre.

Esta especificación es abierta: cualquier herramienta puede leer y escribir archivos `.sakbe`.
