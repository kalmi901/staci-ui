from __future__ import annotations
import pandas as pd
import numpy as np
import json

from functools import cached_property, lru_cache
from pathlib import Path
from typing import Dict, Any

from src.results.hydraulic.base import EPSHydraulicResults, ResultType
from src.services.run_storage import resolve_run_dir

NODE_RESULTS_KEYS = ("pressure", "head", "demand")
LINK_RESULTS_KEYS = ("flowrate", "velocity", "headloss", "status")


@lru_cache(maxsize=64)
def _read_csv_cached(path: str) -> pd.DataFrame:
    df = pd.read_csv(Path(path), index_col="time")
    return df.apply(pd.to_numeric, errors="coerce")

class WntrCsvResults(EPSHydraulicResults):
    def __init__(self, run_state: Dict[str, Any]) -> None:
        self.run_state = run_state
        self.run_id = run_state["run_id"]
        self.run_dir = resolve_run_dir(self.run_id)
        manifest_path = self.run_dir / "run.json"
        
        self.manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    @property
    def backend(self) -> str:
        return "wntr"
    
    
    @cached_property
    def times(self) -> np.ndarray[tuple[Any, ...], np.dtype[Any]]:
        df = self._get_dataframe("node", "pressure")
        if df is None:
            raise ValueError(
                f"Node result 'pressure' is not available."
            )
        return df.index.to_numpy(dtype=np.int64)
    
    @property
    def node_attributes(self) -> list[str]:
        return list(NODE_RESULTS_KEYS)

    @property
    def link_attributes(self) -> list[str]:
        return list(LINK_RESULTS_KEYS)
    
    def node_frame(self, attribute: str, time_index: int) -> pd.Series:
        df = self._get_dataframe("node", attribute)
        if df is None:
            raise KeyError(
                f"Node result '{attribute}' is not available."
            )
        return df.iloc[time_index]
    
    
    def link_frame(self, attribute: str, time_index: int) -> pd.Series | None:
        df = self._get_dataframe("link", attribute)
        if df is None:
            raise KeyError(
                f"Link result '{attribute}' is not available."
            )
        return df.iloc[time_index]
    
    def value_range(
        self,
        type: ResultType,
        attribute: str
    ) -> tuple[float | None, float | None]:
       ranges = self.run_state.get("ranges", {})
       vrange = ranges.get(attribute)
       if not vrange:
           return None, None
       
       return vrange.get("min"), vrange.get("max")
    
    def _get_file(
        self,
        type: ResultType,
        attribute: str
    ) -> Path | None:
        
        filename = (
            self.manifest
            .get("files", {})
            .get(f"{type}s", {})
            .get(attribute)
        )
        if not filename:
            return None
        
        path = (self.run_dir / filename).resolve()
        if not path.is_relative_to(self.run_dir):
            raise ValueError(
                f"Invalid result file path: {filename}"
            )
        return path

        
    def _get_dataframe(
        self,
        type: ResultType,
        attribute: str
    ) -> pd.DataFrame | None:
        fname = self._get_file(type, attribute)
        
        if not fname:
            return None
        
        return _read_csv_cached(str(fname))
        