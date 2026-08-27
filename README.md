# STACI UI

A lightweight web interface for demonstrating and inspecting the **STACI hydraulic solver** on EPANET network models.

The application is built with Python and Dash. It can load EPANET `.inp` files, run STACI extended-period simulations, and visualize hydraulic results stored in HDF5 output.

> **Status:** proof-of-concept / demonstration application. The project is under active development and is being prepared for containerized deployment.

## Features

- Upload and inspect EPANET `.inp` network models
- Preview network topology
- Run STACI extended-period hydraulic simulations
- Read STACI HDF5 result files without converting them to an intermediate format
- Visualize node and link quantities by timestep
- Inspect tank results and solver convergence state
- Keep solver execution, result storage, visualization, and UI logic separated

A WNTR-based backend may also be present during development for validation and comparison, but STACI is the primary solver targeted by this application.

## Project structure

```text
staci-ui/
│
├── app.py
├── requirements.txt
├── requirements-deploy.txt
├── README.md
├── LICENSE
├── .gitignore
├── .dockerignore
│
├── assets/
│
├── src/
│   ├── bin/
│   │   └── staci/
│   │       ├── windows/
│   │       │   └── x64/
│   │       └── linux/
│   │           └── x64/
│   │
│   ├── solver/
│   ├── services/
│   ├── results/
│   ├── visualization/
│   └── ui/
│
└── data/
    ├── uploads/
    └── runs/
```

## Local development

### Python

The application is currently developed and tested with:

`CPython 3.13.1 (64-bit)`
Python 3.13 is therefore the recommended development runtime.
Other Python versions have not yet been validated with the pinned
dependency set.

 Create and activate a virtual environment, then install the project dependencies:

```bash
python -m venv staci-env
```

Windows:

```powershell
.\staci-env\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The development server is available at:

```text
http://localhost:8050
```

## Configuration

The application can read authentication settings from environment variables:

```text
DASH_USER
DASH_PASSWORD
DASH_AUTH_SECRET
```

Additional deployment-specific configuration may be added as containerization is completed.

## STACI

STACI is a separate C++ hydraulic-network solver developed at the BME Department of Hydrodynamic Systems.

Upstream repository:

https://github.com/hoscsaba/staci

This repository contains the user-interface and integration layer. STACI itself is a separate project and is **not covered by this repository's license**.

For reproducible builds, deployment uses a pinned STACI revision rather than an unpinned `master` branch. The currently tested revision is `892e0a2a02c2ef0da944dfa138df74d39ed12f13`.

## EPANET compatibility

-During validation with WNTR-generated EPANET input files, a few input-format compatibility differences were identified in the tested STACI revision, including:
+The current STACI integration and EPANET compatibility checks were tested against:
+
+`STACI commit 892e0a2a02c2ef0da944dfa138df74d39ed12f13`
+
+During validation with WNTR-generated EPANET input files, a few input-format compatibility differences were identified in this revision, including:

 - `HH:MM:SS` versus `HH:MM` formatting in `[TIMES]`
 - midnight representation as `00:00 AM` versus `12:00 AM`
 - `=` versus `IS` in the action branch of `[RULES]`

 After these formatting adjustments, the tested extended-period simulation reproduced the expected hydraulic behaviour well.

 ## Deployment

The application is intended to be distributed as a Docker image and served with Gunicorn.

The planned deployment model is:

```text
STACI build stage
        ↓
Python/Dash runtime image
        ↓
Gunicorn
        ↓
containerized STACI UI
```

Runtime data such as uploaded networks and simulation results should be stored outside the container image using a persistent volume.

## License

The original code in this repository is released under the **MIT License**.

Third-party software, including STACI and its dependencies, remains subject to its own licensing terms.
