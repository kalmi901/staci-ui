# Docker daemon watchdog

Optional host-level monitoring for an active but unresponsive Docker daemon.
It does not probe the web app or measure simulation duration.

The timer starts three minutes after boot and schedules each check 60 seconds
after the previous check completes. Each Docker API probe allows 30 seconds,
with a further five seconds before forced termination of the probe process.
Three consecutive failures request a Docker restart, with at least ten minutes
between restart requests. Successful probes clear the failure count. Inactive
Docker services are skipped, respecting deliberate stops; systemd's Docker
service restart policy handles process exits.

A restart may interrupt simulations and affects all containers on this host.
The watchdog requests an asynchronous systemd restart; it does not guarantee
recovery from a stuck stop operation. Persistent failures can trigger repeated
requests after each cooldown; there is no total retry limit or alert delivery.

## Install

From the repository root, using a sudo-capable account:

```bash
sudo install -m 0755 deploy/docker-watchdog/docker-watchdog /usr/local/sbin/docker-watchdog
sudo install -m 0644 deploy/docker-watchdog/docker-watchdog.service /etc/systemd/system/docker-watchdog.service
sudo install -m 0644 deploy/docker-watchdog/docker-watchdog.timer /etc/systemd/system/docker-watchdog.timer
sudo systemctl daemon-reload
sudo systemctl enable --now docker-watchdog.timer
sudo systemctl status docker-watchdog.timer --no-pager
```

This enables monitoring without restarting Docker. Repeat the installation
commands after changing the source files; repository edits alone do not update
the installed copies. State is kept in `/var/lib/docker-watchdog`.

## Logs and disabling

Failures, restart requests, and cooldown messages go to the systemd journal:

```bash
sudo journalctl -u docker-watchdog.service --since "24 hours ago"
sudo journalctl -u docker-watchdog.service -f
sudo journalctl -u docker.service --since "24 hours ago"
```

To disable monitoring, including a check currently running:

```bash
sudo systemctl disable --now docker-watchdog.timer
sudo systemctl stop docker-watchdog.service
```

This does not stop Docker or undo a restart request already submitted.
