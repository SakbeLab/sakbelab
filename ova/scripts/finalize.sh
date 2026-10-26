#!/usr/bin/env bash
# Deja la VM lista para exportar: pantalla de bienvenida, primer arranque y limpieza.
set -euo pipefail

# Pantalla de la consola: muestra la dirección para abrir en el navegador.
cat > /etc/issue <<'ISSUE'

  SakbeLab: emulador de redes open source

  Abrí en tu navegador:  http://\4
  (En VirtualBox con NAT:  http://localhost:8080)

  Usuario: root  Contraseña: sakbe   (cambiala con el comando passwd)

ISSUE
cp /etc/issue /etc/issue.net

# Primer arranque: claves SSH e identificador de máquina propios de cada copia.
cat > /etc/systemd/system/sakbe-firstboot.service <<'UNIT'
[Unit]
Description=SakbeLab: preparación del primer arranque
Before=ssh.service
ConditionPathExists=!/var/lib/sakbe-firstboot.done

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'ssh-keygen -A && systemd-machine-id-setup && touch /var/lib/sakbe-firstboot.done'

[Install]
WantedBy=multi-user.target
UNIT
systemctl enable sakbe-firstboot.service

# Limpieza para que la OVA pese lo menos posible.
apt-get -y autoremove --purge
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/install.sh
journalctl --vacuum-time=1s || true
rm -f /etc/ssh/ssh_host_*
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id
history -c || true
dd if=/dev/zero of=/zero bs=1M status=none || true
rm -f /zero
sync
