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
  jq \
  docker.io \
  docker-compose-plugin

systemctl enable --now docker

if id ubuntu >/dev/null 2>&1; then
  usermod -aG docker ubuntu || true
fi

echo "Bootstrap complete. Docker version:"
docker --version || true
