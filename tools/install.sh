#!/usr/bin/env bash
# Instala SakbeLab (Fase 0) en Debian 13 o Ubuntu 24.04.
#
# Uso, como root en la VM:
#   curl -fsSL https://raw.githubusercontent.com/SakbeLab/sakbelab/main/tools/install.sh | bash
#
# Variables opcionales: SAKBE_BRANCH (main), SAKBE_PORT (80).
set -euo pipefail

REPO="${SAKBE_REPO:-https://github.com/SakbeLab/sakbelab.git}"
BRANCH="${SAKBE_BRANCH:-main}"
PORT="${SAKBE_PORT:-80}"
PREFIX=/opt/sakbe
FRR_FALLBACKS=(quay.io/frrouting/frr:10.2.1 quay.io/frrouting/frr:9.1.3 frrouting/frr:v8.4.0)

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Ejecutá este script como root (por ejemplo: sudo bash install.sh)." >&2
  exit 1
fi

say "Instalando dependencias del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q docker.io iproute2 iptables util-linux git python3 python3-venv curl ca-certificates
systemctl enable --now docker

say "Descargando SakbeLab ($BRANCH)"
if [ -d "$PREFIX/src/.git" ]; then
  git -C "$PREFIX/src" fetch --depth 1 origin "$BRANCH"
  git -C "$PREFIX/src" reset --hard FETCH_HEAD
else
  git clone --depth 1 -b "$BRANCH" "$REPO" "$PREFIX/src"
fi

say "Instalando el backend"
python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install -q --upgrade pip
"$PREFIX/venv/bin/pip" install -q --force-reinstall --no-deps "$PREFIX/src/backend"
"$PREFIX/venv/bin/pip" install -q "$PREFIX/src/backend"
ln -sf "$PREFIX/venv/bin/sakbe" /usr/local/bin/sakbe

say "Copiando plantillas y ejemplos"
mkdir -p "$PREFIX/templates" "$PREFIX/labs" "$PREFIX/examples"
for f in "$PREFIX"/src/templates/*.yml; do
  dest="$PREFIX/templates/$(basename "$f")"
  [ -e "$dest" ] || cp "$f" "$dest"
done
cp "$PREFIX"/src/examples/*.yml "$PREFIX/examples/"

say "Descargando la imagen del router FRR"
frr_tpl="$PREFIX/templates/frr.yml"
frr_image="$(sed -n 's/^image:[[:space:]]*//p' "$frr_tpl")"
if ! docker pull -q "$frr_image"; then
  for candidate in "${FRR_FALLBACKS[@]}"; do
    if docker pull -q "$candidate"; then
      sed -i "s#^image:.*#image: $candidate#" "$frr_tpl"
      frr_image="$candidate"
      break
    fi
  done
fi
docker image inspect "$frr_image" >/dev/null || { echo "No se pudo descargar ninguna imagen de FRR." >&2; exit 1; }
docker pull -q alpine:3.20 || echo "Aviso: no se pudo descargar alpine:3.20 (plantilla linux-host)."

say "Creando el servicio sakbe"
cat > /etc/systemd/system/sakbe.service <<EOF
[Unit]
Description=SakbeLab
After=docker.service network-online.target
Requires=docker.service

[Service]
Environment=SAKBE_DATA=$PREFIX
ExecStart=$PREFIX/venv/bin/uvicorn sakbe.api.main:app --host 0.0.0.0 --port $PORT
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable sakbe >/dev/null
systemctl restart sakbe

for _ in $(seq 1 20); do
  curl -fs "http://127.0.0.1:$PORT/api/v1/health" >/dev/null && break
  sleep 1
done

suffix=""
[ "$PORT" = "80" ] || suffix=":$PORT"
say "SakbeLab está listo"
echo "Abrí en tu navegador:"
for ip in $(hostname -I); do
  case "$ip" in 172.17.*|*:*) ;; *) echo "  http://$ip$suffix" ;; esac
done
echo
echo "Prueba de la Fase 0 desde esta consola:"
echo "  sakbe --server http://127.0.0.1$suffix deploy $PREFIX/examples/fase0.yml"
