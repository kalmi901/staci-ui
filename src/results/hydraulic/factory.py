from __future__ import annotations

from typing import Any, Dict

from src.results.hydraulic.base import EPSHydraulicResults
from src.results.hydraulic.staci_hdf5 import StaciHDF5Results
from src.results.hydraulic.wntr_csv import WntrCsvResults


def open_eps_hydraulic_results(
    run_state: Dict[str, Any], *, user_id: str
) -> EPSHydraulicResults:

    backend = run_state.get("backend")

    if run_state.get("status") != "success":
        raise ValueError("Cannot open results from an unsuccessful hydraulic run.")

    if backend == "wntr":
        return WntrCsvResults(run_state, user_id=user_id)

    elif backend == "staci":
        return StaciHDF5Results(run_state, user_id=user_id)

    raise ValueError(f"Unsupported hydraulic result backend: {backend!r}")
