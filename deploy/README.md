# VPS deployment

Run these commands from the repository root. Install Docker Engine and Docker
Compose first, and ensure the current user can access Docker.

## HTTPS application

Point the `hydroreact.org` DNS A record at the VPS public IPv4 address. Any AAAA
record must also point at this VPS. Allow inbound TCP ports 80 and 443 in the
host and provider firewalls. For another domain, edit the root `Caddyfile`.

```bash
cp -n .env.example .env
chmod 600 .env
```

Set `DASH_USER`, `DASH_PASSWORD`, and `DASH_AUTH_SECRET` in `.env`, keeping
`STACI_UI_ENV=production`. Generate a secret with `openssl rand -hex 32`.
Never commit `.env`.

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=50 caddy
```

Visit https://hydroreact.org and sign in with the configured credentials.
Caddy manages HTTPS certificates and forwards requests to the app on its
internal port 8050. Named volumes retain application data and Caddy state.
Both services use `restart: unless-stopped`; also ensure the Docker service
is enabled at boot.

After updating application code, run `docker compose up -d --build` again
during a maintenance window: replacing the app can interrupt simulations.
Do not use `docker compose down -v` unless you intend to delete stored data
and certificate state.
