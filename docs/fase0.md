# Prueba de la Fase 0

Objetivo: dos routers conectados que se hacen ping desde la consola web.

La Fase 0 usa routers **FRR** (FRRouting) en contenedores Docker: son libres, no necesitan imágenes de fabricante y cualquiera puede reproducir la prueba.

## 1. Preparar la VM

- Debian 13 (o Ubuntu 24.04) sin entorno gráfico, con *SSH server*.
- 4 GB de RAM, 2 vCPU y 40 GB de disco.
- Red en modo NAT o bridge, con salida a internet para la instalación.

## 2. Instalar

Entrá a la VM como root (o con `sudo -i`) y ejecutá:

```bash
apt-get install -y curl
curl -fsSL https://raw.githubusercontent.com/SakbeLab/sakbelab/main/tools/install.sh | bash
```

Al terminar, el script muestra la dirección para abrir en el navegador, por ejemplo `http://192.168.56.101`.

## 3. Crear y encender el lab

**Desde el navegador:** en *Nuevo lab desde YAML*, tocá **Cargar ejemplo**, luego **Crear lab** y después **Encender**.

**Desde la consola de la VM:**

```bash
sakbe --server http://127.0.0.1 deploy /opt/sakbe/examples/fase0.yml
```

## 4. Probar

1. En la tarjeta del lab, tocá **Consola** en R1.
2. Esperá unos 40 segundos a que OSPF forme la adyacencia y ejecutá:

```
show ip ospf neighbor
show ip route ospf
ping 2.2.2.2
```

3. Detené el ping con `Ctrl+C`.

La prueba pasa si `show ip ospf neighbor` muestra a 2.2.2.2 en estado `Full` y el ping a 2.2.2.2 responde.

## 5. Guardar, exportar y apagar

- **Guardar config:** copia la configuración actual de cada router dentro del lab.
- **Exportar YAML:** descarga el lab completo, listo para compartir y volver a crear con `sakbe deploy`.
- **Apagar:** destruye los contenedores y los cables; la definición del lab se conserva.

## Si algo falla

```bash
systemctl status sakbe          # estado del servicio
journalctl -u sakbe -n 50       # últimos mensajes
docker ps                       # contenedores de los routers
```

Reportá el problema como *Issue* en GitHub, con la salida de esos comandos.
