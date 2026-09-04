from __future__ import annotations
import h5py
import numpy as np
import pandas as pd
import json
from functools import cached_property
from typing import Dict, Any

from src.results.hydraulic.base import EPSHydraulicResults, ResultType
from src.services.run_storage import resolve_run_dir

STACI_NODE_DATASETS = {
    "pressure" : "/nodes/pressure_head",
    "head"      : "/nodes/head",
    "demand"    : "/nodes/demand"
}

STACI_LINK_DATASETS = {
    "flowrate"  : "/links/flow_rate",
    "velocity"  : "/links/velocity",
    "headloss"  : "/links/headloss",
    "status"    : "/links/status"    
}

STACI_RANGE_KEYS = {
    ("node", "pressure"): "pressure_head",
    ("node", "head"): "head",
    ("node", "demand"): "demand",
    ("link", "flowrate"): "flow_rate",
    ("link", "velocity"): "velocity",
    ("link", "headloss"): "headloss",
    ("link", "status"): None,
}

# --- Helpers --- 
def _decode_strings(values) -> list[str]:
    return [
        value.decode("utf-8")
        if isinstance(value, (bytes, np.bytes_))
        else str(value)
        for value in values
    ]

def _get_dataset(
    h5: h5py.File,
    path: str
) -> h5py.Dataset:
    obj = h5.get(path)
    
    if obj is None:
        raise KeyError(
            f"HDF5 dataset not found: {path}"
        )
        
    if not isinstance(obj, h5py.Dataset):
        raise TypeError(
            f"Expected dataset at '{path}', "
            f"got {type(obj).__name__}."
        )

    return obj
    

class StaciHDF5Results(EPSHydraulicResults):
    def __init__(self, run_state: Dict[str, Any]):        
        self.run_state = run_state
        self.run_id = run_state["run_id"]
        self.run_dir = resolve_run_dir(self.run_id, "hydraulic")
        manifest_path = self.run_dir / "run.json"
        
        self.manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        
        files = self.manifest.get("files", {})
        h5_path = files.get("hdf5")
        meta_path = files.get("metadata")
        if not h5_path:
            raise ValueError(
                "STACI run manifest does not contain an HDF5 result path."
            )
            
        if not meta_path:
            raise ValueError(
                "STACI run manifes does not contain an metadata result path."
            )
        
        self.h5_path = (self.run_dir / h5_path).resolve()
        self.meta_path = (self.run_dir / meta_path).resolve()

        if not self.h5_path.is_relative_to(self.run_dir):
            raise ValueError("Invalid HDF5 result path.")

        if not self.meta_path.is_relative_to(self.run_dir):
            raise ValueError("Invalid metadata result path.")
        
        if not self.h5_path.exists():
            raise FileNotFoundError(
                f"STACI result file does not exist: {self.h5_path}"
            )
        
        if not self.meta_path.exists():
            raise FileNotFoundError(
                f"STACI result file does not exist: {self.meta_path}"
            )
            
    @property
    def backend(self) -> str:
        return "staci"
    
    @cached_property
    def metadata(self) -> Dict[str, Any]:
        if self.meta_path is None or not self.meta_path.exists():
            return {}

        return json.loads(
            self.meta_path.read_text(encoding="utf-8")
        )
        
    @cached_property
    def times(self) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        with h5py.File(self.h5_path, "r") as h5:
            ds = _get_dataset(h5, "/time")
            return np.asarray(ds[:], dtype=np.int64)
        
    @cached_property
    def node_ids(self) -> list[str]:
        with h5py.File(self.h5_path, "r") as h5:
            ds = _get_dataset(h5, "/nodes/id")
            return _decode_strings(ds[:])
    
    @cached_property  
    def link_ids(self) -> list[str]:
        with h5py.File(self.h5_path, "r") as h5:
            ds = _get_dataset(h5, "/links/id")
            return _decode_strings(ds[:])
        
    @property
    def node_attributes(self) -> list[str]:
        return list(STACI_NODE_DATASETS)

    @property
    def link_attributes(self) -> list[str]:
        return list(STACI_LINK_DATASETS)
    
    def node_frame(self, attribute: str, time_index: int) -> pd.Series:
        dataset = STACI_NODE_DATASETS.get(attribute)
        
        if dataset is None:
            raise KeyError(
                f"Unknown STACI node result: {attribute}"
            )
            
        with h5py.File(self.h5_path, "r") as h5:
            ds = _get_dataset(h5, dataset)
            values = np.asarray(ds[time_index, :])
            
        return pd.Series(
            values,
            index=self.node_ids,
            name=int(self.times[time_index]),
        )
        
    def link_frame(self, attribute: str, time_index: int) -> pd.Series | None:
        dataset = STACI_LINK_DATASETS.get(attribute)
        if dataset is None:
            raise KeyError(
                f"Unknown STACI link result: {attribute}"
            )
            
        with h5py.File(self.h5_path, "r") as h5:
            ds = _get_dataset(h5, dataset)
            values = np.asarray(ds[time_index, :])
            
        return pd.Series(
            values,
            index=self.link_ids,
            name=int(self.times[time_index]),
        )
    
    def value_range(
        self,
        type: ResultType,
        attribute: str
    ) -> tuple[float | None, float | None]:
        range_key = STACI_RANGE_KEYS.get((type, attribute))

        if range_key is None:
            return None, None

        info = (
            self.metadata
            .get("ranges", {})
            .get(range_key, {})
        )

        return info.get("min"), info.get("max")
    
    def frame_converged(self, time_index: int) -> bool:
        with h5py.File(self.h5_path, "r") as h5:
            obj = h5.get("/simulation/converged")

            if obj is None:
                return True

            if not isinstance(obj, h5py.Dataset):
                raise TypeError(
                    "Expected '/simulation/converged' to be a dataset."
                )

            return bool(obj[time_index])
    