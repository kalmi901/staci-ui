# STACI UI

A lightweight web interface for loading, running, and inspecting hydraulic network models with **STACI**.

The application is built with Python and Dash. It supports EPANET `.inp` models, STACI extended-period hydraulic simulation, network partitioning through `staci_split`, and interactive Plotly-based visualization of model and simulation results.

> **Status:** demonstration / engineering application under active development. Hydraulic simulation, network visualization, network partitioning, and a Docker deployment for WordPress embedding are implemented.

## Features

### Network model

- Upload EPANET `.inp` files
- Parse and summarize network models with WNTR
- Preview network topology and static node/link properties
- Configure manual visualization ranges for network attributes
- Keep uploaded models and runtime results separated by generated model/run IDs

### Hydraulic simulation

- Run **STACI EPS** as the primary hydraulic backend
- Run **WNTR** as a reference backend
- Use the timing options stored in the input model or override simulation duration and hydraulic timestep
- Store STACI hydraulic results in HDF5 and read them directly for visualization
- Store WNTR reference results as per-run CSV files
- Visualize node pressure, head, and demand together with link flow rate, velocity, and headloss
- Step through hydraulic timesteps or play the result as an animation
- Highlight non-converged STACI frames and report failed-frame counts

### Network partitioning

- Run the native **`staci_split`** optimizer on the active network model
- Select the target number of communities
- Configure genetic-algorithm population size, generation count, mutation probability, crossover probability, and random seed
- Visualize partition memberships by node color
- Filter the displayed communities
- Highlight links crossing community boundaries

The partitioning page exposes **modularity with topology-based edge weighting**.

## Architecture

The application keeps UI state lightweight and stores solver files on the server side.

```text
Dash callbacks
      ↓
application services
      ↓
STACI / STACI_SPLIT runtime
      ↓
per-run server-side files
      ↓
result adapters
      ↓
Plotly visualization
```

Browser-side stores contain identifiers and lightweight metadata rather than solver output paths or full hydraulic result arrays.

## Project structure

```text
staci-ui/
├── app.py
├── Dockerfile
├── compose.yaml
├── Caddyfile
├── deploy/               # VPS deployment guide, WordPress plugin and watchdog
├── requirements.txt
├── requirements-deploy.txt
├── assets/
├── src/
│   ├── config.py
│   ├── results/          # hydraulic result adapters
│   ├── services/         # model, hydraulic and partition workflows
│   ├── staci/            # native STACI process invocation/configuration
│   ├── ui/               # Dash pages, callbacks and application shell
│   └── visualisation/    # Plotly network visualization
└── data/                 # runtime data
    ├── uploads/
    └── runs/
```

## Configuration

The Docker deployment configures the application through environment variables.

| Variable | Purpose | Default / notes |
| --- | --- | --- |
| `STACI_UI_URL_PREFIX` | Dash URL prefix | `/staci-app/`; must match the proxy and WordPress embed |
| `STACI_UI_DATA_DIR` | Runtime data directory | Docker sets `/data` |
| `STACI_TIMEOUT_SECONDS` | Native solver timeout | `300` |
| `PORT` | Gunicorn listening port | `8050` |
| `DASH_DEBUG` | Dash debug mode | `0` |
| `STACI_EXECUTABLE` | Path to the STACI executable | Docker sets `/opt/staci/staci` |
| `STACI_SPLIT_EXECUTABLE` | Path to `staci_split` | Docker sets `/opt/staci/staci_split` |

An example production environment file is provided as `.env.example`.

Authentication is handled by WordPress and Caddy. Never expose the application
port publicly: access must pass through the supplied Caddy configuration.

## Docker deployment

The Docker image uses a multi-stage build:

```text
Debian STACI build stage
        ↓
pinned STACI revision
        ↓
staci + staci_split
        ↓
Python runtime image
        ↓
Gunicorn
        ↓
Dash application
```

The image currently pins STACI to revision:

```text
c52ec0424ed5e088a47c7e2a629216d777bab5c4
```

The build enables the STACI optimizer targets required for `staci_split` and verifies the runtime shared-library dependencies before completing the image.

### Build

```bash
docker build -t staci-ui .
```

### WordPress deployment

The supplied Compose stack runs Caddy, WordPress, MariaDB and STACI. A one-shot
initialization service installs WordPress with the administrator configured in
`.env`, preserving existing installations. Only Caddy
publishes ports. It checks the WordPress session before forwarding every request
under `/staci-app/`, including Dash callbacks and assets. WordPress displays the
existing UI through the `[staci_tool]` shortcode supplied by the STACI Tool plugin.

Follow [the VPS deployment guide](deploy/README.md) to configure `.env`, initialize
WordPress, activate STACI Tool and Force Login, and create the tool page.

Uploaded models and solver run directories remain under `/data/uploads` and
`/data/runs` in the `staci-data` volume. Storage is shared between authenticated
users, without per-user ownership or a history browser.

### Logs

Application workflow events and callback exceptions are written through Python logging to the process output. With Docker they can be inspected using:

```bash
docker compose logs -f app
```

Gunicorn and application logs are therefore available through the normal container logging mechanism rather than a separate application log file.


## STACI

STACI is a separate C++ hydraulic-network solver developed at the **BME Department of Hydrodynamic Systems**.

Upstream repository:

https://github.com/hoscsaba/staci

This repository contains the web UI and integration layer. STACI itself is a separate project and is **not covered by this repository's license**.

## Runtime data

Runtime data is organized by generated identifiers. Uploaded source models and individual hydraulic/partition runs are stored separately.

The application does not currently implement automatic retention or pruning of runtime data. For persistent deployments, cleanup can be handled by the surrounding server/container infrastructure according to the desired retention policy.

## Current scope

Implemented:

- Network upload and inspection
- Static network visualization
- STACI and WNTR hydraulic simulation
- Hydraulic timestep visualization and animation
- STACI convergence-state visualization
- `staci_split` modularity-based network partitioning
- Community filtering and boundary-link visualization
- Docker/Gunicorn deployment
- WordPress session checks at the reverse proxy

## License

The original code in this repository is released under the **MIT License**.

Third-party software, including STACI and its dependencies, remains subject to its own licensing terms.
