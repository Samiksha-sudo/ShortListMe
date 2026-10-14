# Deploy on a DigitalOcean Droplet

1. **Droplet:** Ubuntu 24.04, Basic $6/mo (1 GB), London, SSH key login. Note its IP.
2. **DNS** (at your registrar): A records `@`, `www` and `api` → the Droplet IP.
3. **On the server** (`ssh root@IP`):
   ```
   git clone https://github.com/Samiksha-sudo/ShortListMe.git && cd ShortListMe
   sh deploy/setup-server.sh
   cp deploy/.env.example deploy/.env && nano deploy/.env     # fill in your values
   docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
   ```
4. Check `https://api.YOURDOMAIN/health` returns `{"status":"ok"}`.
5. **Stripe webhook:** endpoint `https://api.YOURDOMAIN/v1/billing/webhook`, copy its `whsec_` into `STRIPE_WEBHOOK_SECRET` in `deploy/.env`, then
   `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d`.
6. **Backups:** install the cron line in `deploy/backup-cron.sh`, and turn on Droplet backups in DigitalOcean.

Update later: `git pull && docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build`.
