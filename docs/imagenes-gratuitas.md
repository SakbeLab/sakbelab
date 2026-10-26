# Imágenes gratuitas para SakbeLab

SakbeLab no incluye ni descarga imágenes. Esta guía lista imágenes que se pueden obtener legalmente sin costo. Revisá siempre los términos de cada fabricante antes de descargar.

| Imagen | Tipo | Cómo se obtiene |
| --- | --- | --- |
| FortiGate VM | QCOW2 | Portal de soporte de Fortinet con cuenta gratuita, licencia de evaluación limitada |
| Juniper vJunos-router y vJunos-switch | QCOW2 | Descarga directa del sitio de Juniper |
| Arista vEOS-lab y cEOS-lab | QCOW2 y Docker | Sitio de Arista con cuenta gratuita |
| MikroTik CHR | QCOW2 | Descarga directa; sin licencia la velocidad queda limitada |
| VyOS | QCOW2 o ISO | Versiones rolling gratuitas desde vyos.io |
| pfSense CE y OPNsense | ISO, se instala en QCOW2 | Descarga directa |
| Nokia SR Linux | Docker | Registro público de contenedores de Nokia |
| FRR | Docker | Imagen oficial pública |
| Hosts Linux (Alpine, Debian, Ubuntu) | QCOW2 y Docker | Imágenes cloud oficiales de cada distribución |

Las imágenes de Cisco no son de descarga libre: se obtienen con licencia (por ejemplo CML Personal) y sus términos limitan dónde se pueden usar.

## Importar imágenes que ya tenés

SakbeLab incluirá un importador compatible con la estructura de carpetas de EVE-NG y PNETLab (por ejemplo `qemu/fortinet-7.2.0/virtioa.qcow2`): detecta fabricante y versión por el nombre de la carpeta y crea la plantilla automáticamente. La responsabilidad sobre la licencia de cada imagen es del usuario.
