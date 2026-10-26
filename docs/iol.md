# Cisco IOL en SakbeLab

IOL corre como un programa de Linux, sin virtualización anidada, y consume poca memoria: es la forma más liviana de tener routers y switches Cisco para labs de CCNA.

## Imágenes y licencia

SakbeLab no incluye ni descarga imágenes IOL. Cada usuario carga las suyas y es responsable de tener una licencia que le permita usarlas fuera del producto de Cisco con el que las obtuvo. Las imágenes que vienen con Cisco Modeling Labs, por ejemplo, están licenciadas solo para usarse dentro de CML.

Si tu imagen necesita un archivo de licencia `iourc`, copialo a `/opt/sakbe/images/iol/iourc`.

## Cargar una imagen

1. Abrí **Imágenes y plantillas** y arrastrá el archivo `.bin`.
2. En la imagen cargada, tocá **Crear plantilla**, o editá las plantillas incluidas **Cisco IOL L3** y **Cisco IOL L2** y elegí la imagen.
3. Las interfaces se llaman `Ethernet0/0`, `Ethernet0/1`... En la plantilla, *Cantidad de interfaces* define cuántas tiene el equipo; cada 4 interfaces se agrega un slot (`Ethernet1/0`...).

## Configuración

- La **configuración inicial** del equipo se aplica solo la primera vez que arranca.
- Después, `write memory` dentro del IOL guarda la configuración en su NVRAM, que se conserva al apagar y encender. Se borra al eliminar el nodo.
- **Guardar configuraciones** en la barra superior lee `show running-config` por la consola y lo guarda en el lab, para exportarlo en el `.sakbe`.

## Cómo funciona

Cada IOL corre dentro de un proceso de SakbeLab (`sakbe.engines.iol_wrapper`) que:

- le da una consola en un pseudo-terminal, disponible desde el navegador;
- traduce sus interfaces (protocolo netio de IOU) a interfaces tap de Linux, que se conectan a los enlaces como las de cualquier otro equipo.

Los archivos de cada equipo quedan en `/opt/sakbe/run/<lab>/<equipo>/`. Si un IOL no arranca, revisá `wrapper.log` en esa carpeta.
