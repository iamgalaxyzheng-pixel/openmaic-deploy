#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo 'Run as root.' >&2
  exit 1
fi

/opt/openmaic/server/preflight.sh

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF

install -m 0755 -d /usr/share/keyrings
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg -o /usr/share/keyrings/tailscale-archive-keyring.gpg
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list -o /etc/apt/sources.list.d/tailscale.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin tailscale

docker version --format 'Docker server {{.Server.Version}}'
docker compose version
tailscale version | head -n 1
systemctl is-active --quiet finance-observatory
systemctl is-active --quiet caddy
test "$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' https://43.162.115.148/)" = 200
echo 'Container and VPN prerequisites installed; finance website still responds.'

