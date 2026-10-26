# OVA de SakbeLab

La OVA se construye con [Packer](https://developer.hashicorp.com/packer) a partir del ISO netinst de Debian 13, de forma reproducible.

## Qué trae

- Debian 13 mínimo, sin entorno gráfico.
- SakbeLab instalado como servicio (`sakbe`), escuchando en el puerto 80.
- Docker con las imágenes libres de FRR (router) y Alpine (host).
- Librerías para Cisco IOL. Ninguna imagen de fabricante.
- Pantalla de consola con la dirección para abrir en el navegador.
- Usuario `root`, contraseña `sakbe`. Cambiala con `passwd` después de importarla.

## Construirla

Necesitás Packer y VirtualBox 7 en la máquina donde construís:

```bash
cd ova
packer init .
packer build .
```

El resultado queda en `output/sakbelab-<versión>.ova`, junto con su `.sha256`. Si Debian publicó una versión más nueva del ISO, pasala con `-var debian_version=13.x.0`; para versiones viejas usá `-var debian_dir=https://cdimage.debian.org/cdimage/archive`.

## Usarla

- **VirtualBox:** Archivo > Importar servicio virtualizado. La red viene en NAT con reenvío de puertos: abrí `http://localhost:8080`; SSH en el puerto 2222.
- **VMware Workstation o Player:** File > Open, elegí la OVA y aceptá el aviso de compatibilidad. Abrí la dirección que muestra la consola de la VM.
- Para nodos QEMU (versión 0.2), activá la virtualización anidada: en VMware, *Virtualize Intel VT-x/EPT or AMD-V/RVI*.
