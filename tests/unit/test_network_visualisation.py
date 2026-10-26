from unittest.mock import patch

import pandas as pd

from src.visualisation.network_preview import (
    make_hydraulic_timestep_figure,
    make_node_preview_figure,
    make_partitioned_network_figure,
)


NETWORK_VIEW_STATE = {
    "model_id": "abcdef123456",
    "nodes": {
        "id": ["A", "B", "C"],
        "type": [
            "Reservoir",
            "Junction",
            "Junction",
        ],
        "x": [0.0, 1.0, 2.0],
        "y": [0.0, 0.0, 0.0],
        "elevation": [100.0, 95.0, 90.0],
        "demand": [0.0, 0.01, 0.02],
    },
    "links": {
        "id": ["P1", "P2"],
        "start_index": [0, 1],
        "end_index": [1, 2],
        "start_node": ["A", "B"],
        "end_node": ["B", "C"],
        "length": [100.0, 200.0],
        "diameter": [0.2, 0.3],
    },
}


class FakeHydraulicResults:
    n_steps = 2
    times = [0, 3600]
    node_attributes = {"pressure"}
    link_attributes = {"flowrate"}

    def node_frame(
        self,
        attribute: str,
        time_index: int,
    ) -> pd.Series:
        assert attribute == "pressure"
        assert time_index == 1

        return pd.Series(
            {
                "A": 20.0,
                "B": 21.0,
                "C": 22.0,
            }
        )

    def link_frame(
        self,
        attribute: str,
        time_index: int,
    ) -> pd.Series:
        assert attribute == "flowrate"
        assert time_index == 1

        return pd.Series(
            {
                "P1": 0.01,
                "P2": 0.02,
            }
        )

    def frame_converged(
        self,
        time_index: int,
    ) -> bool:
        return time_index == 1


def test_node_preview_uses_shared_attribute_renderer() -> None:
    figure = make_node_preview_figure(
        NETWORK_VIEW_STATE,
        node_color_by="elevation",
        link_color_by="length",
        node_cmin=90.0,
        node_cmax=100.0,
        link_cmin=100.0,
        link_cmax=200.0,
    )

    trace_names = {
        trace.name  # type: ignore[arg-type]
        for trace in figure.data
    }

    assert "Nodes" in trace_names
    assert "length bin 1" in trace_names
    assert figure.layout.uirevision == "abcdef123456"


def test_node_preview_reports_invalid_color_range() -> None:
    figure = make_node_preview_figure(
        NETWORK_VIEW_STATE,
        node_color_by="elevation",
        node_cmin=100.0,
        node_cmax=90.0,
    )

    assert figure.layout.annotations
    assert (
        figure.layout.annotations[0].text
        == (
            "Node color minimum must not be greater "
            "than maximum."
        )
    )


def test_hydraulic_figure_uses_shared_renderer() -> None:
    run_state = {
        "run_id": "123456abcdef",
        "model_id": "abcdef123456",
    }

    with patch(
        "src.visualisation.network_preview."
        "open_eps_hydraulic_results",
        return_value=FakeHydraulicResults(),
    ):
        figure = make_hydraulic_timestep_figure(
            network_view_state=NETWORK_VIEW_STATE,
            run_state=run_state,
            time_index=1,
            node_result="pressure",
            link_result="flowrate",
            node_cmin=20.0,
            node_cmax=22.0,
            link_cmin=0.01,
            link_cmax=0.02,
        )

    assert figure.layout.uirevision == "123456abcdef"
    assert "1 h" in figure.layout.title.text

    assert "Nodes" in {
        trace.name  # type: ignore[arg-type]
        for trace in figure.data
    }


def test_partition_figure_marks_boundary_links() -> None:
    partition_state = {
        "run_id": "fedcba654321",
        "model_id": "abcdef123456",
        "node_community": {
            "A": 0,
            "B": 0,
            "C": 1,
        },
    }

    figure = make_partitioned_network_figure(
        network_view_state=NETWORK_VIEW_STATE,
        partition_state=partition_state,
        selected_communities=[],
        show_boundary_links=True,
    )

    boundary_trace = next(
        trace
        for trace in figure.data
        if trace.name == "Boundary links"  # type: ignore[arg-type]
    )

    assert tuple(boundary_trace.x) == (1.0, 2.0, None)  # type: ignore[arg-type]
    assert figure.layout.uirevision == "fedcba654321"