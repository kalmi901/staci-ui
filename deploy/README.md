# WordPress deployment on an Ubuntu VPS

Run commands from the repository root with Docker Engine and Docker Compose
installed. This stack installs a new WordPress site at the domain root. An
existing WordPress site must be migrated separately; do not point it at an
existing database without a backup and a migration plan.

## Configuration

Point the domain's A record at the VPS; any AAAA record must also point there.
Allow inbound TCP 80 and 443. Caddy handles HTTPS and access checks.

```bash
cp -n .env.example .env
chmod 600 .env
openssl rand -hex 32
openssl rand -hex 32
```

Set `SITE_DOMAIN` to the hostname only (default `hydroreact.org`). Set separate
`WORDPRESS_DB_PASSWORD` and `MARIADB_ROOT_PASSWORD` values using the generated
secrets. Never commit `.env`.
ySet `WORDPRESS_ADMIN_USER`, `WORDPRESS_ADMIN_PASSWORD`, and `WORDPRESS_ADMIN_EMAIL`
for the initial WordPress administrator. Keep the password in `.env` only; use
single quotes around its value if it contains `$` or `#` characters.
Database passwords initialize a new database volume; changing `.env` later
does not rotate credentials in an existing database.

## Start and configure WordPress

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=50 caddy wordpress
```

The one-shot `wordpress-init` service installs WordPress with the site title
`STACI` and the configured administrator. Caddy starts after this service exits
successfully. If WordPress is already installed, initialization leaves users,
passwords and settings untouched. Changing the administrator values in `.env`
does not reset an existing account.

Open `https://<your-domain>/wp-admin/` and sign in with the configured credentials.

1. Under Plugins, activate **STACI Tool**, mounted from this repository.
2. Install and activate **Force Login** (`wp-force-login`).
3. Create a page, for example `/tool/`, with a Shortcode block containing
   `[staci_tool]`. A full-width page template gives the existing UI more room.
4. Publish the page and use WordPress accounts to access it.

Initialization only installs WordPress and its administrator; the plugin and
page steps above are manual. The four application services keep running;
`wordpress-init` normally appears as `Exited (0)` in `docker compose ps -a`.

Keep WordPress at the domain root, with its public URL matching `SITE_DOMAIN`.
The supplied stack relies on WordPress's logged-in cookie reaching
`/staci-app/`. Do not cache the tool page, `/staci-app/*`, or the authentication
endpoint in WordPress/CDN cache plugins. The proxy sends `Cache-Control: no-store`
for the tool. The official WordPress image recognizes Caddy's forwarded HTTPS
header; WordPress and the database have no published ports.

## Access boundary

Caddy forwards each tool request's cookies to
`/wp-admin/admin-ajax.php?action=staci_tool_access`. The plugin verifies the
logged-in cookie, its expiry and its WordPress session token, returning 204 and
`X-Staci-Access: allowed` only on success. POST requests additionally require an
Origin matching the WordPress site's origin to prevent cross-site requests.

Caddy removes client-supplied access headers and requires the explicit success
header, so a missing/disabled plugin or an ordinary WordPress 200 page does not
grant access. Failed authentication returns 401; a failed origin check returns
403. After logging in again, reload the tool page. Logout blocks subsequent
requests, but does not cancel a computation already running or erase results
already displayed in the browser.

Dash relies on WordPress/Caddy for login and uses the verified user headers only
to attribute application logs. Its container is reachable only on a
private Docker network shared with Caddy. Never publish port 8050 or attach an
untrusted container to that network. WordPress cookies are removed before
requests reach Dash. Force Login protects WordPress pages; Caddy and the STACI
Tool plugin protect the separately running application.

## Verify before use

- In a private browser window, `/tool/` requires WordPress login.
- Anonymous GETs to `/staci-app/`, `/staci-app/_dash-layout`, and
  `/staci-app/assets/css/01_base.css` return 401, including with a forged
  `X-Staci-Access: allowed` header.
- Anonymous POSTs to `/staci-app/_dash-update-component` return 401.
- A logged-in ordinary subscriber can load the iframe, navigate all existing
  pages, upload a model, partition it and run/display hydraulic results.
- A logged-in POST with a missing/foreign Origin returns 403.
- After logging out in another tab, subsequent tool requests return 401.
- With STACI Tool disabled, the tool remains inaccessible.
- Host port 8050 is not exposed (`docker compose ps`).

Configuration and syntax checks:

```bash
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
docker compose exec wordpress php -l /var/www/html/wp-content/plugins/staci-tool/staci-tool.php
```

## Data and updates

The existing `staci-data`, `caddy-data` and `caddy-config` volumes are retained;
`wordpress-data` and `wordpress-db` hold the new site. Keep the same Compose
project name/directory when upgrading to reuse the existing volumes. Back up
volumes before switching the live site. The four application services restart
unless stopped; the initialization service exits after completing its check.

Models/results are not assigned to users, and there is no previous-run browser.
Logged-in users are trusted with the shared tool; their data is not isolated.

## User-attributed application logs

STACI Tool 1.1.1 returns `X-Staci-User-Id` and a URL-encoded
`X-Staci-User-Login` after validating the WordPress session. Caddy removes any
client-supplied values and forwards only the verified headers. Keep the app
private on the solver network; these headers are not standalone credentials.

Existing Python logs now include the user ID/login and explicit UTC timestamps.
Events outside a request have `user_id=- user=-`. Solver execution, result
classification and browser workflows are unchanged. Filenames remain in upload
events and are linked to run events by `model_id`; this is not a run database.

Compose enables a rotating `/var/log/staci/application.log`: 5 MiB per file,
five backups (approximately 30 MiB total, apart from an oversized single event).
Docker console output is retained as before. File rotation supports the current
single Gunicorn worker with four threads, not multiple writing processes.
Local development without `STACI_LOG_DIR` keeps console-only logging.

The new `staci-logs` volume is writable only in the app and mounted read-only
in WordPress. The app sets its directory group to GID 33 (`www-data`), mode 2750,
and creates files with mode 0640. Include this volume in future backups.

Administrators can open **Tools → STACI napló**. The page uses `manage_options`,
allows only the six known filenames, escapes log content, and reads at most the
last 256 KiB / 500 lines. Refresh is manual. The volume is outside the web root;
there is no public log endpoint. Historical Docker logs are not imported.

Deploy the plugin, Caddy configuration and Python changes together; recreate
app/WordPress to apply the volume mounts and environment. No database migration
or solver rebuild is required. Check two user identities, forged headers,
anonymous requests, administrator/subscriber access and rotated-file readability.

After code updates, run `docker compose up -d --build` during a maintenance
window; replacing the app can interrupt simulations. Do not run
`docker compose down -v` unless intentionally deleting all stored data and
certificate state. Pin/update container image versions according to your VPS
maintenance policy.
