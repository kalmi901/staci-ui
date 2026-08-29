from __future__ import annotations
from typing import Dict, Any
from src.results.hydraulic.base import EPSHydraulicResults
from src.results.hydraulic.wntr_csv import WntrCsvResults
from src.results.hydraulic.staci_hdf5 import StaciHDF5Results


def open_eps_hydraulic_results(
    run_state: Dict[str, Any],
) -> EPSHydraulicResults:

    backend = run_state.get("backend")

    if run_state.get("status") != "success":
        raise ValueError(
            "Cannot open results from an unsuccessful hydraulic run."
        )

    if backend == "wntr":
        return WntrCsvResults(run_state)

    elif backend == "staci":
        return StaciHDF5Results(run_state)

    raise ValueError(
        f"Unsupported hydraulic result backend: {backend!r}"
    )