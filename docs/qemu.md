# Imágenes QEMU (QCOW2) en SakbeLab

El motor QEMU corre máquinas virtuales completas a partir de imágenes QCOW2 (o IMG, VMDK, ISO): FortiGate, Cisco vIOS y CSR, Palo Alto, MikroTik CHR, VyOS, Arista vEOS, pfSense y cualquier appliance que se distribuya como disco.

## Requisitos

- QEMU instalado en el servidor (la OVA y el instalador ya lo traen).
- **Virtualización anidada** activada en el hipervisor donde corre la VM de SakbeLab. Sin ella, las VMs funcionan por emulación de software, mucho más lento.
  - VMware: en la configuración de la VM, *Processors > Virtualize Intel VT-x/EPT or AMD-V/RVI*.
  - VirtualBox: *Sistema > Procesador > Habilitar VT-x/AMD-V anidado*.
  - Proxmox: tipo de CPU `host`.

Comprobá que hay aceleración: dentro de la VM, `ls /dev/kvm` debe existir. Si no existe, el editor muestra un aviso cuando el lab tiene equipos QEMU.

## Cargar una imagen y crear su plantilla

1. **Imágenes y plantillas > Imágenes:** arrastrá el archivo `.qcow2` (o copialo por SCP a `/opt/sakbe/images/qemu/`).
2. En la imagen, tocá **Crear plantilla** y ajustá:
   - **Tarjeta de red:** `virtio` rinde mejor; usá `e1000` si el appliance no reconoce virtio.
   - **Disco:** `virtio` por defecto; `IDE` para imágenes viejas.
   - **Consola:** *Serial* para routers y firewalls (texto); *Gráfica (VNC)* para equipos con escritorio.
   - **Configuración inicial por cloud-init:** actívala para VyOS y otros equipos que leen su config de un disco cloud-init. SakbeLab arma ese disco con lo que escribas en la configuración inicial del nodo.
   - RAM, vCPU e interfaces según el appliance.

## Cómo funciona

- Cada equipo corre como un proceso `qemu-system`. SakbeLab crea un **disco overlay** sobre tu imagen base, así la base no se modifica y lo que guardes (por ejemplo con `write memory`) persiste al apagar y encender. Se borra al eliminar el nodo.
- Cada interfaz es un dispositivo tap que se conecta a los enlaces como el de cualquier otro equipo.
- La consola serial se ve en el navegador. Si la plantilla usa consola gráfica (VNC), al abrir la consola se ve la pantalla del equipo, con un botón para enviar Ctrl+Alt+Supr. Ambas se pueden abrir en otra ventana.
- Los archivos de cada equipo quedan en `/opt/sakbe/run/<lab>/<equipo>/`.

## Licencias

SakbeLab no incluye ni descarga imágenes. Cargá las tuyas, con la licencia que corresponda. En [imágenes gratuitas](imagenes-gratuitas.md) hay appliances que se obtienen legalmente sin costo.
