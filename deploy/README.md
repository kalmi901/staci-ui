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
docker compose build --pull wordpress wordpress-init
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

## PHP security updates (2026-10-21)

The public WordPress service uses Apache/mod_php. CVE-2026-109618 and
CVE-2026-109619 affect PHP itself and can be reached before WordPress/plugin
authentication. The Python/Dash/Celery/native STACI runtime does not use PHP,
but the website and the application's WordPress authentication gateway do.
WordPress also has access to its database and read-only STACI model/result/log
volumes, so a PHP compromise can disclose those files.

The complete fix is a patched PHP runtime. The official PHP 8.3 branch requires
**8.3.36 or later**; other supported branch minima are 8.2.35, 8.4.27 and 8.5.12.
See the [PHP security advisory](https://www.php.net/archive/2026.php#2026-10-21-5).

Both WordPress images now build from `deploy/wordpress/Dockerfile`, which rejects
unpatched, unsupported and prerelease upstream PHP versions. The build also
disables session upload progress before request parsing as defense in depth;
this setting alone is not a complete mitigation. No public diagnostic endpoint
or WordPress plugin check is used to claim runtime protection.

On an existing deployment, first back up the WordPress database and site volume,
keep the same Compose project/directory, and then run:

```bash
docker compose build --pull wordpress wordpress-init
docker compose run --rm --no-deps --entrypoint php wordpress /usr/local/lib/staci/check-php-security.php
docker compose run --rm --no-deps --entrypoint php wordpress-init /usr/local/lib/staci/check-php-security.php
docker compose up -d --no-deps --force-recreate wordpress
docker compose exec -T wordpress php /usr/local/lib/staci/check-php-security.php
docker compose exec -T wordpress php -r 'exit(ini_get("session.upload_progress.enabled") ? 1 : 0);'
docker compose ps wordpress
```

If the upstream images have not yet been rebuilt with patched PHP, the build
fails before replacing the live container. Do not bypass the version check;
obtain a verified patched image before proceeding. Pulling a tag or restarting
an old container does not prove the runtime was patched. Recreating WordPress
restarts all Apache/PHP workers; the solver services need no restart.

Afterward verify the homepage, login, anonymous `/staci-app/` rejection,
authenticated tool access and administrator log access (and downloads when enabled). Run the PHP
test suites only with disposable log/data filesystems, never production volumes.
The CLI check validates the installed upstream PHP binary; an internal Apache
request should also confirm the web worker's version and loaded configuration.
Remove any temporary diagnostic file immediately and never expose `phpinfo()`.

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
private Docker network shared with Caddy, Redis and the Celery worker. Never publish port 8050 or attach an
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

Dash 4.4.1 transfers server-side request headers into the background callback
context. Worker log filters read that context when no Flask request is active;
identity is never taken from model data or user-supplied callback arguments.
Celery's logging setup signal installs the same handlers/formatter as the web
process. Keep Redis and workers private on the solver network.

STACI Tool 1.2.0 returns `X-Staci-User-Id` and a URL-encoded
`X-Staci-User-Login` after validating the WordPress session. Caddy removes any
client-supplied values and forwards only the verified headers. Keep the app
private on the solver network; these headers are not standalone credentials.

Existing Python logs now include the user ID/login and explicit UTC timestamps.
Events outside a request have `user_id=- user=-`. Solver execution, result
classification and browser workflows are unchanged. Filenames remain in upload
events and are linked to run events by `model_id`; this is not a run database.

Compose enables a rotating `/var/log/staci/application.log`: 5 MiB per file,
five backups (approximately 30 MiB total, apart from an oversized single event).
Docker console output is retained for both app and worker. A POSIX file lock
serializes appends and rotation across Gunicorn and Celery worker processes.
Each writer reopens the current file under that lock to avoid writing into an
already rotated archive.
Local development without `STACI_LOG_DIR` keeps console-only logging.

The `staci-logs` volume is writable in app/worker and mounted read-only in
WordPress. The network-isolated `logs-init` service prepares ownership for
UID 10001 (`staci`), GID 33 (`www-data`), directory mode 2750 and file mode 0640,
including existing archives. App and worker wait for initialization and run
under the unprivileged application user with supplementary group 33. Existing
setgid permissions are preserved when already configured. Files use mode 0640.
Include this volume in future backups.

Administrators can open **Tools → STACI napló**. The default run list supports
user/file/ID search, state and local-date filters, 50 rows per page and a copyable
per-run reproduction summary. Display dates use Europe/Budapest (including DST);
raw records remain UTC. The page uses `manage_options`, allows only the six known
filenames and escapes all log content. Refresh is manual. The raw viewer remains
available and reads at most the last 256 KiB / 500 lines.

Hydraulic, partitioning and flushing callbacks receive a task-local
`execution_id` before validation. This is distinct from the solver's `run_id`, which is allocated later. Existing log
messages keep their text and gain this correlation field; additional `STACI_RUN`
JSON events record requested settings, source/Python/WNTR fingerprints, timeout,
prepared input SHA-256, effective hydraulic options, partition XML or flushing
JSON, solver binary SHA-256 (for STACI), elapsed time and completion information. No solver
arguments, results or browser callback return values are changed. Metadata
inspection failures produce warnings without cancelling a calculation. The
source digest covers app.py, Python source and requirements files; it identifies
code but is not a stored checkout, image or environment lockfile.

The list scans at most 6 MiB per known log file, keeps at most 500 attempts/legacy
events and 24 KiB of log detail per attempt, with explicit truncation notices.
Legacy records without correlation IDs remain separate events; overlapping runs
are never paired by user/model/time guesses. Missing start or finish events are
labelled incomplete, not running or successful. Completion with reported failed
frames, STACI warnings or partial flushing results is labelled with a warning.
Completion alone does not certify numerical correctness.

The run detail view offers **Feltöltött fájl letöltése** for a retained, unambiguous
run whose original upload is still readable. WordPress mounts `staci-data`
read-only at `/var/lib/staci-data`, outside its web root. The `admin-post.php`
handler checks `manage_options`, GET and a session-bound, execution-specific
WordPress nonce before indexing the retained logs. Only the log's validated
`model_id` and stored filename select `/var/lib/staci-data/uploads/<model_id>/<filename>`;
request-supplied paths are ignored. Symlinked directories/files, path traversal,
missing uploads and non-regular files are rejected. Responses stream the original
bytes as an attachment with private/no-store caching; there is no public file URL.
Missing files or logs return 404, and invalid/expired links return 403. Refresh
the run details to obtain a new link. Existing uploads work without migration
when normal directory/file permissions allow UID 33 (`www-data`) to read them.

The download is the original upload, not the prepared solver input: hydraulic
time overrides may change the run's `input.inp` and its recorded SHA-256. Run
input copies already produced by the services remain in the data volume.
Reproduction requires retaining those inputs and matching code/binaries as well
as the displayed settings. Log rotation can remove this history; this feature is
not a durable audit database. The volume is outside the web root;
there is no public log endpoint. Historical Docker logs are not imported.

When the patched WordPress images described above are already deployed, update
the plugin directory and Compose file for the download feature, then run
`docker compose up -d --no-deps wordpress` to apply its new read-only
mount. This download change requires no Python/Caddy/solver change, application
image rebuild, data migration or app/worker restart. The PHP security changes
still require rebuilding and deploying the patched WordPress images as described
above. Keep the existing Compose project/volume names.

For the initial user-attributed logging setup, deploy the plugin, Caddy
configuration and Python changes together; recreate
app/worker/WordPress to apply the volume mounts and environment. No database
migration is required. Build the merged image with the STACI revision pinned
in Dockerfile before deployment. When upgrading an existing root-owned data
volume to main's non-root runtime, stop app/worker and migrate `/data` ownership
to UID/GID 10001 before starting the new services. `logs-init` only initializes
the log volume; it does not modify uploaded models or solver results.
Check two user identities, forged headers,
anonymous requests, administrator/subscriber access and rotated-file readability.

After code updates, run `docker compose up -d --build` during a maintenance
window; replacing the app can interrupt simulations. Do not run
`docker compose down -v` unless intentionally deleting all stored data and
certificate state. Pin/update container image versions according to your VPS
maintenance policy.

### Run dashboard verification

Run `python -m unittest discover -s tests -p 'test_*.py'` in the application
environment. Run `tests/test_log_viewer.php`, `tests/test_run_dashboard.php` and
`tests/test_input_download.php` in separate disposable PHP 8.3 containers as UID 33,
with empty writable `/var/log/staci` and `/var/lib/staci-data` tmpfs mounts;
these tests write synthetic logs and must never run against production volumes.
The tests cover concurrent attempt IDs, unchanged callback arguments/results,
prepared input fingerprints, rotation, incomplete/legacy events, escaping,
filters, time zones, access control and bounded reads.
Download checks also cover original bytes, real HTTP attachment headers/status,
execution-bound nonces, missing/rotated history, path traversal, symlinks and
unreadable files. CI runs all three PHP suites without production volumes.
