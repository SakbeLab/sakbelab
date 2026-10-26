# Labs como código

Un lab de SakbeLab se puede dibujar en el editor, describir en YAML o programar en Python. Las tres formas producen el mismo lab: lo que creás por código aparece en el lienzo, y lo que dibujás se exporta como YAML.

## Instalar la CLI y el SDK en tu computadora

Solo necesitás Python 3.11 o superior:

```bash
pip install "git+https://github.com/SakbeLab/sakbelab#subdirectory=backend"
```

Indicá la dirección de tu SakbeLab una vez:

```bash
export SAKBE_SERVER=http://192.168.56.101      # Linux o macOS
setx SAKBE_SERVER http://192.168.56.101        # Windows
```

## SDK de Python

```python
from sakbe import Lab

lab = Lab("anillo-ospf", server="http://192.168.56.101")
routers = [lab.node(f"R{i}", template="frr") for i in range(1, 5)]

# Anillo: eth1 de cada router con eth2 del siguiente.
for i, r in enumerate(routers):
    lab.link(r["eth1"], routers[(i + 1) % 4]["eth2"])

routers[0].config("""
    hostname R1
    interface eth1
     ip address 10.0.12.1/30
     ip ospf area 0
""")

lab.deploy()              # crea (o reemplaza) el lab y enciende los equipos
lab.wait_ready()          # espera a que todos estén encendidos
lab.export("anillo.sakbe", author="Victor Rodas")
```

| Método | Qué hace |
| --- | --- |
| `lab.node(nombre, template, ram, cpus, x, y, config)` | Agrega un equipo. Sin `x` e `y`, se ubica en una grilla. |
| `nodo["eth1"]` | Una interfaz, para usar en `link`. |
| `lab.link(a, b)` | Conecta dos interfaces. |
| `nodo.config(texto)` | Configuración inicial; la sangría común se elimina. |
| `lab.note(texto, x, y)` | Nota en el lienzo. |
| `lab.deploy(replace=True, start=True)` | Crea o reemplaza el lab en el servidor y lo enciende. |
| `lab.start()`, `lab.stop()`, `nodo.start()`, `nodo.stop()` | Encender y apagar. |
| `lab.wait_ready(timeout=120)` | Espera a que todos los equipos estén encendidos. |
| `lab.save_configs()` | Trae al lab la configuración actual de los equipos. |
| `lab.export("x.sakbe")`, `lab.export("x.yml")` | Descarga el lab. |
| `Lab.from_yaml("x.yml")`, `Lab.load("nombre")` | Abre un lab desde un archivo o desde el servidor. |

## YAML y CLI

```yaml
name: fase0
nodes:
  R1: {template: frr, config: "hostname R1\n"}
  R2: {template: frr}
  SW1: {template: ethernet-switch}
links:
  - [R1:eth1, SW1:e0]
  - [R2:eth1, SW1:e1]
```

```bash
sakbe deploy fase0.yml           # crear y encender
sakbe list                       # labs y su estado
sakbe start fase0 R1             # encender un equipo
sakbe stop fase0                 # apagar el lab
sakbe export fase0 --save        # guardar configuraciones y exportar fase0.sakbe
sakbe import fase0.sakbe --name copia
sakbe templates                  # plantillas disponibles
sakbe upload imagen.qcow2        # subir una imagen
```
