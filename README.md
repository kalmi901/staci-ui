# STACI UI

A lightweight web interface for demonstrating and inspecting the **STACI hydraulic solver** on EPANET network models.

The application is built with Python and Dash. It can load EPANET `.inp` files, run STACI extended-period simulations, and visualize hydraulic results stored in HDF5 output.

> **Status:** proof-of-concept / demonstration application. The project is under active development and is being prepared for containerized deployment.

## Target Features

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
├── assets/
├── src/
│   ├── bin/
│   │   └── staci/
│   ├── staci/
│   ├── services/
│   ├── results/
│   ├── visualization/
│   ├── ui/
|   └── config.py
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

### Runtime data

By default, runtime data is stored under `data/`.

The location can be overridden with:

`STACI_UI_DATA_DIR`

## STACI

STACI is a separate C++ hydraulic-network solver developed at the BME Department of Hydrodynamic Systems.

Upstream repository:

https://github.com/hoscsaba/staci

This repository contains the user-interface and integration layer. STACI itself is a separate project and is **not covered by this repository's license**.

For reproducible builds, deployment uses a pinned STACI revision rather than an unpinned `master` branch. The currently tested revision is `c52ec0424ed5e088a47c7e2a629216d777bab5c4`.

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
