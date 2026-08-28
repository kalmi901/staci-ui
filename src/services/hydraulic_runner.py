from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Dict

import uuid
import json
import pandas as pd
import numpy as np
import wntr

from src.staci.eps import run_staci_eps
from src.config import RUN_ROOT


# -- Helpers --
def _dataframe_range(df: pd.DataFrame, unit: str = "none") -> dict[str, str | float | None]:
    if df.empty:
        return {"min": None, "max": None}
    values = df.to_numpy()
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "unit": unit,
            "min": None,
            "max": None,
        }
    return {
        "unit": unit,
        "min": float(finite.min()),
        "max": float(finite.max()),
    }


def run_wntr(
    inp_path: Path | str,
    model_id: str,
    run_id: str,
    run_dir: Path
) -> Dict[str, Any]:
    
    # Run the WNTR Simulatior
    wn = wntr.network.WaterNetworkModel(str(inp_path))
    sim = wntr.sim.WNTRSimulator(wn)
    result = sim.run_sim()
    
    if result.node is None or result.link is None:
        raise RuntimeError("WNTR hydraulic simulation failed.")
    
    def _process_and_write_results(
        results_group: Dict[str, Any],
        *,
        type: Literal["node", "link"],
        attr_units: Dict[str, Any],
        run_dir: Path
    ):
        files: Dict [str, str] = {}
        ranges: Dict[str, Dict[str, float | str | None]] = {}
        
        for attr, unit in attr_units.items():
            if attr not in results_group:
                continue
            df = results_group[attr]
            if not isinstance(df, pd.DataFrame):
                continue
            
            ranges[attr] = _dataframe_range(df, unit)
            
            file = str(run_dir / f"{type}_{attr}.csv")
            df.index.name = "time"
            df.to_csv(file)
            files[attr] = file
        return files, ranges
    
    node_attr_units = {
        "head"      : "m",
        "pressure"  : "m",
        "demand"    : "m3/s"
    }

    link_attr_units = {
        "flowrate" : "m3/s",
        "velocity" : "m/s",
        "headloss" : "m",
        "status"   : "none"
    }    
     
    node_files, node_ranges = _process_and_write_results(
        result.node,
        type="node",
        attr_units=node_attr_units,
        run_dir=run_dir 
    )
    
    link_files, link_ranges = _process_and_write_results(
        result.link,
        type="link",
        attr_units=link_attr_units,
        run_dir=run_dir 
    )
            
    ranges = node_ranges | link_ranges
    
    time_values: list[int] = []
    if result.node:
        first_result = next(iter(result.node.values()))
        time_values = [
            int(t)
            for t in first_result.index.to_list()
        ]
    elif result.link:
        first_result = next(iter(result.link.values()))
        time_values = [
            int(t)
            for t in first_result.index.to_list()
        ]
    
    duration_seconds = (
        time_values[-1]
        if time_values
        else 0
    )
    
    frames = len(time_values)
    
    return {
        "run_id" : run_id,
        "model_id" : model_id,
        "backend"  : "wntr",
        "status"   : "success",
        "created_at" : datetime.now(timezone.utc).isoformat(),
        "files" : {
            "node" : node_files,
            "link" : link_files
        },
        "summary": {
            "duration_seconds" : duration_seconds,
            "n_steps"   : frames
        },
        "ranges" : ranges
    }
    
    
    


def run_staci(
    inp_path: Path | str,
    model_id: str,
    run_id: str,
    run_dir: Path
) -> Dict[str, Any]:
    
    result = run_staci_eps(
        inp_path=Path(inp_path),
        output_prefix=run_dir / "results"
    )
    
    meta = result.meta
    simulation = meta.get("simulation", {})
    ranges     = meta.get("ranges", {})
    
    success   = (
        result.returncode == 0 and
        result.h5_path.exists() and
        result.meta_path.exists() and
        simulation.get("status") == "complete" )
    
    if not success:
        return {
            "run_id": run_id,
            "model_id": model_id,
            "backend": "staci",
            "status": "failure",
            "returncode": result.returncode,
            "stdout_log": str(result.stdout_path),
            "stderr_log": str(result.stderr_path),
        }
       
    frames = int(simulation.get("frames", 0))

    return {
        "run_id"   : run_id,
        "model_id" : model_id,
        "backend"  : "staci",
        "status"   : "success",
        "created_at" : datetime.now(timezone.utc).isoformat(),
        "files" : {
            "hdf5" : str(result.h5_path),
            "metadata" : str(result.meta_path),
            "csv" : {
                "nodes": str(run_dir / "results-nodes.csv"),
                "links": str(run_dir / "results-links.csv"),
                "tanks": str(run_dir / "results-tanks.csv"),
                "summary": str(run_dir / "results-summary.csv"),
            },
            "stdout" : str(result.stdout_path),
            "stderr" : str(result.stderr_path)
        },
        "summary" : {
            "duration_seconds" : simulation.get("duration_seconds", ""),
            "n_steps" : frames,
            "failed_frames": simulation.get("failed_frames", 0),
        },
        "ranges" : ranges,
        
        "staci" : {
            "generator":  meta.get("generator"),
            "format": meta.get("format"),
            "warnings": meta.get("warnings", [])
        }
    }

def call_hydraulic_simulator(
    inp_path: Path | str,
    *,
    model_id: str,
    backend: Literal["wntr", "staci"]
):
    inp_path = Path(inp_path)
    if not inp_path.exists():
        raise FileNotFoundError(f"INP file does not exist: {inp_path}")
    
    run_id = uuid.uuid4().hex[:12]
    run_dir = Path(RUN_ROOT) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    if backend == "wntr":
        return run_wntr(inp_path, model_id, run_id, run_dir)
        
    elif backend == "staci":
        return run_staci(inp_path, model_id, run_id, run_dir)
        
    raise NotImplementedError(
        f"Hydraulic backend is not implemented yet: {backend}"
    )
