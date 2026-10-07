from src.visualisation.flushing import (
    make_flushing_scenario_figure,
)


NETWORK_VIEW_STATE = {
    "nodes": {
        "id": ["A", "B", "C"],
        "type": [
            "Reservoir",
            "Junction",
            "Junction",
        ],
        "x": [0.0, 1.0, 2.0],
        "y": [0.0, 0.0, 0.0],
    },
    "links": {
        "id": ["P1", "P2"],
        "start_node": ["A", "B"],
        "end_node": ["B", "C"],
    },
}

SCENARIO_STATE = {
    "scenario_id": "B",
    "pipes": [
        {
            "pipe_id": "P1",
            "flow_m3s": 0.01,
            "velocity_mps": 0.7,
            "absolute_velocity_mps": 0.7,
            "baseline_velocity_mps": 0.01,
            "above_threshold": True,
            "newly_above_threshold": True,
        },
        {
            "pipe_id": "P2",
            "flow_m3s": -0.002,
            "velocity_mps": -0.2,
            "absolute_velocity_mps": 0.2,
            "baseline_velocity_mps": 0.01,
            "above_threshold": False,
            "newly_above_threshold": False,
        },
    ],
    "hydrants": [
        {
            "node_id": "B",
            "status": "ok",
            "flow_m3s": 0.01,
            "pressure_head_m": 21.5,
        }
    ],
}


def test_make_flushing_coverage_figure_marks_results() -> None:
    figure = make_flushing_scenario_figure(
        NETWORK_VIEW_STATE,
        SCENARIO_STATE,
        map_mode="coverage",
        candidate_hydrant_ids=["B", "C"],
    )

    traces = {
        trace.name: trace   # type: ignore[arg-type]
        for trace in figure.data
    }

    assert "Newly above threshold" in traces
    assert "Below threshold" in traces
    assert "Candidate hydrants" in traces
    assert "Open hydrants" in traces

    assert tuple(
        traces["Open hydrants"].x # type: ignore
    ) == (1.0,)

    assert tuple(
        traces["Candidate hydrants"].x # type: ignore
    ) == (2.0,)


def test_make_flushing_velocity_figure_adds_scale() -> None:
    figure = make_flushing_scenario_figure(
        NETWORK_VIEW_STATE,
        SCENARIO_STATE,
        map_mode="velocity",
    )

    scale_trace = next(
        trace
        for trace in figure.data
        if trace.name == "Velocity scale"   # type: ignore[arg-type]
    )

    assert scale_trace.marker.showscale is True # type: ignore[arg-type]

    assert "Open hydrants" in {
        trace.name  # type: ignore[arg-type]
        for trace in figure.data
    }