#!/usr/bin/env bash
set -euo pipefail

# Basic host bootstrap for Assignment 6 automation:
# - Install Docker Engine + Compose plugin
# - Enable docker on boot
# - Add ubuntu user to docker group
#
# After provisioning, copy your repo to the VM and run:
#   docker compose up -d --build

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  gnupg \
  jq

# Ensure we don't end up with Podman's docker shim (`podman-docker`) which breaks `docker compose ...`.
apt-get remove -y podman-docker podman podman-compose 2>/dev/null || true
apt-get autoremove -y || true

# Install Docker Engine + Compose v2 from Docker's official apt repo (jammy).
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu jammy stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y --no-install-recommends \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

systemctl enable --now docker

if id ubuntu >/dev/null 2>&1; then
  usermod -aG docker ubuntu || true
fi

echo "Bootstrap complete. Docker version:"
docker --version || true
docker compose version || true
