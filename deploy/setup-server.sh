#!/bin/sh
# One-time setup on a fresh Ubuntu 24.04 Droplet. Run as root:  sh setup-server.sh
set -eu
apt-get update
apt-get install -y ca-certificates curl git ufw
curl -fsSL https://get.docker.com | sh
# Firewall: SSH + web only
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
# 1 GB swap so the frontend build doesn't run out of memory on the small plan
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
echo "Server ready. Next: git clone the repo, create deploy/.env, then start the stack (see deploy/README.md)."
