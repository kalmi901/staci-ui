# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations

from typing import Any, Dict

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.staci.optimizer_limits import (
    MAX_OPTIMIZER_GENERATIONS,
    MAX_OPTIMIZER_POPULATION,
    MAX_PARTITION_COMMUNITIES,
    MAX_RANDOM_SEED,
)
from src.ui import ids
from src.ui.pages.components import (
    create_active_model_section,
    create_network_display_controls,
    create_number_field,
    create_page_header,
    create_run_section,
    create_settings_grid,
)
from src.visualisation.common import make_empty_network_figure


def render_success_alert(partition_state: Dict[str, Any]):
    n_nodes = partition_state.get("n_nodes", "—")
    n_community_members = partition_state.get("n_community_members", {})
    n_communities = partition_state.get("n_communities", 0)

    community_summary = " · ".join(
        f"Community {community_id}: {member_count} nodes"
        for community_id, member_count in sorted(n_community_members.items())
    )

    return dbc.Alert(
        className="upload-alert",
        color="success",
        children=[
            html.Div("Network partitioning finished", style={"fontWeight": 800}),
            html.Div(
                children=[
                    html.Span(
                        f"{n_nodes} nodes partitioned into {n_communities} communities"
                    ),
                ],
                className="mt-1",
            ),
            html.Div(
                community_summary or "No community information available.",
                className="mt-1 small",
            ),
        ],
    )


def _label_with_help(
    label: str,
    help_text: str,
    help_id: str,
):
    return html.Div(
        className="part-field-label",
        children=[
            dbc.Label(label, className="mb-0"),
            html.Span(
                "?",
                id=help_id,
                className="part-help-icon",
            ),
            dbc.Tooltip(
                help_text,
                target=help_id,
                placement="right",
            ),
        ],
    )


# Setup Card
def _create_setup_card():
    def _create_partition_settings():
        return html.Div(
            className="setup-section",
            children=[
                html.H3("Partitioning settings"),
                html.P(
                    "Choose the target community count and how "
                    "network links contribute to the partitioning "
                    "objective."
                ),
                dcc.Store(
                    id=ids.PART_OBJECTIVE,
                    data="modularity",
                ),
                create_settings_grid(
                    [
                        create_number_field(
                            "Number of communities",
                            ids.PART_NCOMM,
                            3,
                            min_value=1,
                            max_value=MAX_PARTITION_COMMUNITIES,
                            step=1,
                            persist=False,
                        ),
                        html.Div(
                            className="settings-field",
                            children=[
                                _label_with_help(
                                    "Edge weighting",
                                    (
                                        "Topology assigns equal weight "
                                        "to all links. Pressure drop "
                                        "weights links by the calculated "
                                        "head loss. Sensitivity weighting "
                                        "uses hydraulic pressure "
                                        "sensitivities."
                                    ),
                                    "part-help-weighting",
                                ),
                                dcc.Dropdown(
                                    id=ids.PART_WEIGHT_TYPE,
                                    options=[
                                        {
                                            "label": "Topology",
                                            "value": "topology",
                                        },
                                        {
                                            "label": "Pressure drop",
                                            "value": "dp",
                                        },
                                        {
                                            "label": "Sensitivity",
                                            "value": "sensitivity",
                                        },
                                    ],
                                    value="topology",
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                            ],
                        ),
                        html.Div(
                            className="settings-field",
                            children=[
                                _label_with_help(
                                    "Sensitivity parameter",
                                    (
                                        "Hydraulic parameter used to "
                                        "calculate sensitivities when "
                                        "sensitivity weighting is "
                                        "selected."
                                    ),
                                    "part-help-sensitivity",
                                ),
                                dcc.Dropdown(
                                    id=ids.PART_WEIGHT_MOD,
                                    options=[
                                        {
                                            "label": ("Friction coefficient"),
                                            "value": "friction_coeff",
                                        },
                                        {
                                            "label": "Pipe diameter",
                                            "value": "diameter",
                                        },
                                        {
                                            "label": "Node demand",
                                            "value": "demand",
                                        },
                                    ],
                                    value="diameter",
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                    disabled=True,
                                ),
                            ],
                        ),
                    ]
                ),
            ],
        )

    def _create_optimizer_settings():
        return html.Div(
            className="setup-section",
            children=[
                html.H3("Optimizer settings"),
                html.P(
                    "Configure the genetic algorithm used to search "
                    "for the partitioning solution."
                ),
                create_settings_grid(
                    [
                        create_number_field(
                            "Population size",
                            ids.PART_POPSIZE,
                            20,
                            min_value=2,
                            max_value=MAX_OPTIMIZER_POPULATION,
                            step=1,
                            persist=False,
                        ),
                        create_number_field(
                            "Generations",
                            ids.PART_NGEN,
                            50,
                            min_value=1,
                            max_value=MAX_OPTIMIZER_GENERATIONS,
                            step=1,
                            persist=False,
                        ),
                        create_number_field(
                            "Mutation probability",
                            ids.PART_PMUT,
                            0.25,
                            min_value=0,
                            max_value=1,
                            step=0.01,
                            persist=False,
                        ),
                        create_number_field(
                            "Crossover probability",
                            ids.PART_PCROSS,
                            0.8,
                            min_value=0,
                            max_value=1,
                            step=0.01,
                            persist=False,
                        ),
                        create_number_field(
                            "Random seed",
                            ids.PART_SEED,
                            12345,
                            min_value=0,
                            max_value=MAX_RANDOM_SEED,
                            step=1,
                            persist=False,
                        ),
                    ]
                ),
            ],
        )

    return dbc.Card(
        className="app-card partition-setup-card",
        children=[
            dbc.CardHeader("Partitioning setup"),
            dbc.CardBody(
                children=[
                    create_active_model_section(
                        ids.PART_ACTIVE_MODEL_SUMMARY,
                    ),
                    html.Hr(),
                    _create_partition_settings(),
                    html.Hr(),
                    _create_optimizer_settings(),
                    html.Hr(),
                    create_run_section(
                        "Run partitioning",
                        ids.PART_RUN_BUTTON,
                        ids.PART_RUN_STATUS,
                        status_class_name="part-run-status",
                    ),
                ]
            ),
        ],
    )


def _create_network_partition_card():

    def _create_plot_toolbar():
        return html.Div(
            className="plot-toolbar",
            children=[
                html.Div(
                    className="plot-control",
                    children=[
                        dbc.Label("Communities"),
                        dcc.Dropdown(
                            id=ids.PART_COMMUNITY_FILTER,
                            options=[],
                            value=[],
                            multi=True,
                            placeholder="All communities",
                            persistence=True,
                            persistence_type="memory",
                        ),
                    ],
                ),
                html.Div(
                    className="plot-control",
                    children=[
                        dbc.Label("Boundary links"),
                        dbc.Switch(
                            id=ids.PART_SHOW_BOUNDARY_LINKS,
                            value=False,
                            label="Highlight",
                            persistence=True,
                            persistence_type="memory",
                        ),
                    ],
                ),
                create_network_display_controls(
                    ids.PART_LINE_WIDTH,
                    ids.PART_MARKER_SIZE,
                    ids.PART_HIDE_NODES,
                ),
            ],
        )

    return dbc.Card(
        className="app-card partition-preview-card",
        children=[
            dbc.CardHeader("Network partitions"),
            dbc.CardBody(
                children=[
                    _create_plot_toolbar(),
                    dcc.Graph(
                        id=ids.PART_NETWORK_GRAPH,
                        className="network-graph",
                        config={"displaylogo": False},
                        figure=make_empty_network_figure(
                            "Run partitioning to view the resulting communities.",
                            icon="🧩",
                            title="No partitioning result yet",
                        ),
                    ),
                ]
            ),
        ],
    )


def create_layout():
    return html.Div(
        className="page partition-page",
        children=[
            # ---- Header ----
            create_page_header(
                "Network Partitioning",
                (
                    "Partition the active network into communities using "
                    "edge weights based on topology, pressure drop, or "
                    "hydraulic sensitivity."
                ),
                "Network Partitioning",
            ),
            # ---- Workspace ---
            html.Div(
                className="analysis-workspace partition-workspace",
                children=[_create_setup_card(), _create_network_partition_card()],
            ),
        ],
    )
