# STACI UI

A lightweight web interface for loading, running, and inspecting hydraulic network models with **STACI**.

The application is built with Python and Dash. It supports EPANET `.inp` models, STACI extended-period hydraulic simulation, network partitioning through `staci_split`, and interactive Plotly-based visualization of model and simulation results.

> **Status:** demonstration / engineering application under active development. Hydraulic simulation, network visualization, network partitioning, Docker deployment, and BasicAuth are implemented. Water-quality and biofilm pages are currently placeholders for future modules.

## Features

### Network model

- Upload EPANET `.inp` files
- Parse and summarize network models with WNTR
- Preview network topology and static node/link properties
- Configure manual visualization ranges for network attributes
- Keep uploaded models and runtime results separated by generated model/run IDs

### Hydraulic simulation

- Run **STACI EPS** as the primary hydraulic backend
- Run **WNTR** as a reference/development backend
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

The current partitioning page exposes **modularity with topology-based edge weighting**. A-/D-optimality and hydraulic sensitivity/pressure-drop weighting are present as future options but are currently disabled in the UI.

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
└── data/                 # local runtime data in development
    ├── uploads/
    └── runs/
```

## Local development

The current development environment uses **CPython 3.13.1 (64-bit)**. Python 3.13 is therefore the recommended development runtime for the pinned dependency set.

Create and activate a virtual environment:

```bash
python -m venv staci-env
```

Windows PowerShell:

```powershell
.\staci-env\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The development server is available by default at:

```text
http://localhost:8050
```

The WNTR backend only requires the Python dependencies. Native STACI execution additionally requires the corresponding STACI executables. Outside Docker they can either be placed under `src/bin/staci/` (`staci.exe` / `staci_split.exe` on Windows) or provided through the `STACI_EXECUTABLE` and `STACI_SPLIT_EXECUTABLE` environment variables.


## Configuration

The application is configured through environment variables.

| Variable | Purpose | Default / notes |
| --- | --- | --- |
| `STACI_UI_ENV` | Application environment | `development`; Docker image sets `production` |
| `DASH_USER` | BasicAuth username | required in production |
| `DASH_PASSWORD` | BasicAuth password | required in production |
| `DASH_AUTH_SECRET` | BasicAuth secret key | required in production |
| `STACI_UI_DATA_DIR` | Runtime data directory | local: `data/`; Docker: `/data` |
| `STACI_TIMEOUT_SECONDS` | Native solver timeout | `300` |
| `PORT` | Dash/Gunicorn listening port | `8050` |
| `DASH_DEBUG` | Dash debug mode | `0` |
| `STACI_EXECUTABLE` | Path to the STACI executable | Docker sets `/opt/staci/staci` |
| `STACI_SPLIT_EXECUTABLE` | Path to `staci_split` | Docker sets `/opt/staci/staci_split` |

An example production environment file is provided as `.env.example`.

Production mode intentionally refuses to start when `DASH_USER`, `DASH_PASSWORD`, or `DASH_AUTH_SECRET` is missing.

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

### Configure credentials

Create a local environment file from the supplied example and set non-default production credentials:

```bash
cp .env.example .env
```

For example:

```text
STACI_UI_ENV=production
DASH_USER=<username>
DASH_PASSWORD=<password>
DASH_AUTH_SECRET=<random-secret>
STACI_TIMEOUT_SECONDS=300
```

Do not commit the populated `.env` file.


### Run with persistent runtime storage

A Docker named volume can be mounted at `/data`:

```bash
docker volume create staci-ui-data

docker run --rm \
  --name staci-ui \
  --env-file .env \
  -p 8050:8050 \
  -v staci-ui-data:/data \
  staci-ui
```

Open:

```text
http://localhost:8050
```

Uploaded models and solver run directories are stored under `/data/uploads` and `/data/runs` inside the container. Mount `/data` to persistent storage when results must survive container replacement.

If persistent storage is not required, the application can run with temporary container storage instead.

### Logs

Application workflow events and callback exceptions are written through Python logging to the process output. With Docker they can be inspected using:

```bash
docker logs -f staci-ui
```

Gunicorn and application logs are therefore available through the normal container logging mechanism rather than a separate application log file.


### Runtime data

By default, runtime data is stored under `data/`.

The location can be overridden with:

`STACI_UI_DATA_DIR`

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
- BasicAuth protection

Currently placeholders / future work:

- Water-quality analysis page
- Biofilm analysis page
- A-/D-optimality workflows
- Sensitivity- and pressure-drop-weighted partitioning controls

## License

The original code in this repository is released under the **MIT License**.

Third-party software, including STACI and its dependencies, remains subject to its own licensing terms.
