# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations
from dash import dcc, html
import dash_bootstrap_components as dbc
from typing import Dict, Any

from src.ui import ids
from src.visualisation.network_preview import make_empty_network_figure


def render_success_alert(partition_state: Dict[str, Any]):
    #run_id = partition_state.get("run_id", "—")
    n_nodes = partition_state.get("n_nodes", '—')
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
                    #html.Span(f"Run ID: {run_id}"),
                    #html.Span(" · "),
                    html.Span(
                        f"{n_nodes} nodes partitioned into "
                        f"{n_communities} communities"
                    ),
                ],
                className="mt-1"
            ),
            html.Div(
                community_summary or "No community information available.",
                className="mt-1 small",
            )
        ]
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
    
    def _create_active_model_section():
        return html.Div(
            className="setup-section",
            children=[
                html.H3("Model summary"),
                html.Div(
                    id=ids.PART_ACTIVE_MODEL_SUMMARY,
                    className="part-active-model-box",
                    children=[
                        html.Div("No active model", className="model-summary-title"),
                        html.P("Go to Load Model and upload an EPANET .inp file first.")
                    ]
                )
            ]
        )
    
    def _create_partition_setup():
        return html.Div(
            className="setup-section",
            children=[
                html.H3("Partitioning"),
                # -- Number of Communities --
                _label_with_help(
                    "Number of communities",
                    (
                        "Target number of network communities. "
                        "The final result may contain fewer non-empty "
                        "communities."
                    ),
                    "part-help-n-comm",
                ),
                dbc.Input(
                    id=ids.PART_NCOMM,
                    type="number",
                    value=3,
                    min=1,
                    step=1
                ),
                # -- Optimization Objectives --
                _label_with_help(
                    "Optimization objective",
                    (
                        "Network partitioning uses modularity. "
                        "A- and D-optimality are sensitivity-based "
                        "node-selection objectives and are currently "
                        "not exposed by this page."
                    ),
                    "part-help-objective"
                ),
                dcc.Dropdown(
                    id=ids.PART_OBJECTIVE,
                    options=[
                        {"label": "Modularity", "value": "modularity"},
                        {"label": "A-optimality", "value": "A-optimality", "disabled": True},
                        {"label": "D-optimality", "value": "D-optimality", "disabled": True}
                    ],
                    value="modularity",
                    clearable=False,
                    persistence=True,
                    persistence_type="memory"
                ),
                # -- Edge weighting --
                _label_with_help(
                    "Edge weighting",
                    (
                        "Topology assigns equal weight to all links. "
                        "Pressure drop weights links by solved headloss. "
                        "Sensitivity weighting uses hydraulic pressure "
                        "sensitivities."
                    ),
                    "part-help-weighting"
                ),
                dcc.Dropdown(
                    id=ids.PART_WEIGHT_TYPE,
                    options=[
                        {"label": "Topology", "value": "topology"},
                        {"label": "Pressure drop", "value": "dp", "disabled": True},
                        {"label": "Sensitivity", "value": "sensitivity", "disabled": True},
                    ],
                    value="topology",
                    clearable=False,
                    persistence=True,
                    persistence_type="memory"
                ),
                # -- Sensitivity Parameter --
                _label_with_help(
                    "Sensitivity Parameter",
                    (
                        "Hydraulic parameter used to calculate "
                        "sensitivities when Sensitivity weighting is "
                        "selected."
                    ),
                    "part-help-sensitivity"
                ),
                dcc.Dropdown(
                    id=ids.PART_WEIGHT_MOD,
                    options=[
                        {"label": "Friction coefficient", "value": "friction_coeff"},
                        {"label": "Pipe diameter", "value": "diameter"},
                        {"label": "Node demand", "value": "demand"}
                    ],
                    value="diameter",
                    clearable=False,
                    persistence=True,
                    persistence_type="memory"
                )
            ]
        )
    
    def _create_ga_setup():
        return html.Div(
            className="setup-section",
            children=[
                html.H3("Genetic algorithm"),
                # -- Population Size --
                _label_with_help(
                    "Population size",
                    (
                        "Number of candidate solutions maintained by "
                        "the genetic algorithm. Larger populations can "
                        "improve exploration but increase runtime."
                    ),
                    "part-help-popsize"
                ),
                dbc.Input(
                    id=ids.PART_POPSIZE,
                    type="number",
                    value="20",
                    min=2,
                    step=1
                ),
                # --  Generations --
                _label_with_help(
                    "Generations",
                    (
                        "Number of genetic-algorithm generations. "
                        "Increasing this value gives the optimizer more "
                        "opportunities to improve the partition."
                    ),
                    "part-help-ngen"
                ),
                dbc.Input(
                    id=ids.PART_NGEN,
                    type="number",
                    value=50,
                    min=1,
                    step=1
                ),
                # -- Mutation Probability --
                _label_with_help(
                    "Mutation probability",
                    (
                        "Probability of applying mutation during "
                        "genetic optimization."
                    ),
                    "part-help-pmut"
                ),
                dbc.Input(
                    id=ids.PART_PMUT,
                    type="number",
                    value=0.25,
                    min=0.0,
                    max=1.0,
                    step=0.01
                ),
                # -- Crossover Probability --
                _label_with_help(
                    "Crossover probability",
                    (
                        "Probability of combining information from "
                        "two parent solutions."
                    ),
                    "part-help-pcross"
                ),
                dbc.Input(
                    id=ids.PART_PCROSS,
                    type="number",
                    value=0.8,
                    min=0.0,
                    max=1.0,
                    step=0.01
                ),
                # -- Seed --
                _label_with_help(
                    "Random seed",
                    (
                        "Seed used by the optimizer. Keeping the same "
                        "seed makes repeated runs more reproducible."
                    ),
                    "part-help-seed",
                ),
                dbc.Input(
                    id=ids.PART_SEED,
                    type="number",
                    value=12345,
                    min=0,
                    step=1,
                ),
            ]
        )
        
    def _create_run_section():
        return html.Div(
            className="setup-section",
            children=[
                dbc.Button(
                    "Run Optimization",
                    id=ids.PART_RUN_BUTTON,
                    color="primary",
                    n_clicks=0,
                    disabled=True,
                    className="primary-action-button"
                ),
                html.Div(
                    className="run-feedback-area",
                    children=[
                        dcc.Loading(
                            type="dot",
                            color="blue",
                            show_initially=False,
                            children=html.Div(
                                id=ids.PART_RUN_STATUS,
                                className="small-status part-run-status"
                            )
                        )
                    ]
                )
            ]
        )
    
    return dbc.Card(
        className="app-card partition-setup-card",
        children=[
            dbc.CardHeader("Partition Setup"),
            dbc.CardBody(
                children=[
                    _create_active_model_section(),
                    html.Hr(),
                    _create_partition_setup(),
                    html.Hr(),
                    _create_ga_setup(),
                    html.Hr(),
                    _create_run_section()
                ]
            )
        ] 
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
                            persistence_type="memory"
                        )
                    ]
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
                            persistence_type="memory"
                        )
                    ]
                )
            ]
        )
    
    return dbc.Card(
        className="app-card partition-preview-card",
        children=[
            dbc.CardHeader("Network Partitions"),
            dbc.CardBody(
                children=[
                    _create_plot_toolbar(),
                    dcc.Graph(
                        id=ids.PART_NETWORK_GRAPH,
                        className="network-graph",
                        config={"displaylogo": False},
                        figure=make_empty_network_figure(
                            "Run optimization to view network partitions."
                        )
                    )
                ]
            )
        ]
    )



def create_layout():
    return html.Div(
        className="page partition-page",
        children=[
            # ---- Header ----
            html.Div(
                className="page-header",
                children=[
                    html.Div(
                        children=[
                            html.H1("Network Partitioning"),
                            html.P("Partition a hydraulic network into sub-networks "
                                   "based on specific criteria, such as topology, "
                                   "sensitivity, or pressure.")
                        ]
                    ),
                    dbc.Badge("Network Partitioning", color="info", className="page-badge")
                ]
            ),
            # ---- Workspace ---
            html.Div(
                className="partition-workspace",
                children=[
                    _create_setup_card(),
                    _create_network_partition_card()
                ]
            )
        ]
        
    )