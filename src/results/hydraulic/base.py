from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Literal

import numpy as np
import pandas as pd

ResultType = Literal["node", "link"]

class EPSHydraulicResults(ABC):
    @property
    @abstractmethod
    def backend(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def times(self) -> np.ndarray:
        raise NotImplementedError

    @property
    def n_steps(self) -> int:
        return len(self.times)

    @property
    @abstractmethod
    def node_attributes(self) -> list[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def link_attributes(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def node_frame(
        self,
        attribute: str,
        time_index: int,
    ) -> pd.Series:
        raise NotImplementedError

    @abstractmethod
    def link_frame(
        self,
        attribute: str,
        time_index: int,
    ) -> pd.Series:
        raise NotImplementedError

    @abstractmethod
    def value_range(
        self,
        type: ResultType,
        attribute: str,
    ) -> tuple[float | None, float | None]:
        raise NotImplementedError

    def frame_converged(self, time_index: int) -> bool:
        return True