# pylint: disable=not-callable
# pyright: reportCallIssue=false 
# Elnémítja a Pylance hibajelzéseit, a dbc komponensekben
from __future__ import annotations
from dash import html
import dash_bootstrap_components as dbc

def _info_card(icon: str, title: str, text: str):
    return dbc.Card(
        className="home-info-card",
        children=[
            html.Div(icon, className="home-info-icon"),
            html.H3(title, className="home-info-title"),
            html.P(text, className="home-info-text"),
        ],
    )
    
def _external_link(icon: str, title: str, text: str, href: str):
    return html.A(
        href=href,
        target="_blank",
        rel="noopener noreferrer",
        className="home-external-link",
        children=[
            html.Div(icon, className="home-external-icon"),
            html.Div(
                children=[
                    html.H4(title),
                    html.P(text),
                ]
            ),
            html.Div("↗", className="home-external-arrow"),
        ],
    )
    
def _overview_diagram():
    # TODO --> ábrára cserélni
    return html.Div(
        className="home-diagram",
        children=[
            html.Div("Concept overview", className="home-diagram-label"),

            html.Div(
                className="home-diagram-canvas",
                children=[
                    html.Div(className="diagram-orbit orbit-a"),
                    html.Div(className="diagram-orbit orbit-b"),

                    html.Div(className="diagram-pipe pipe-1"),
                    html.Div(className="diagram-pipe pipe-2"),
                    html.Div(className="diagram-pipe pipe-3"),
                    html.Div(className="diagram-pipe pipe-4"),

                    html.Div(className="diagram-node node-1"),
                    html.Div(className="diagram-node node-2"),
                    html.Div(className="diagram-node node-3"),
                    html.Div(className="diagram-node node-4"),
                    html.Div(className="diagram-node node-5"),

                    html.Div(
                        className="diagram-core",
                        children=[
                            html.Div("EPANET", className="diagram-core-title"),
                            html.Div("hydraulics", className="diagram-core-subtitle"),
                        ],
                    ),

                    html.Div(
                        className="diagram-biofilm-panel",
                        children=[
                            html.Div("Biofilm layer", className="diagram-panel-title"),
                            html.Div(className="biofilm-layer"),
                            html.Div(className="microbe microbe-a"),
                            html.Div(className="microbe microbe-b"),
                            html.Div(className="microbe microbe-c"),
                        ],
                    ),

                    html.Div(
                        className="diagram-quality-panel",
                        children=[
                            html.Div("Water quality", className="diagram-panel-title"),
                            html.Div(className="quality-wave wave-a"),
                            html.Div(className="quality-wave wave-b"),
                            html.Div(className="quality-wave wave-c"),
                        ],
                    ),
                ],
            ),

            html.Div(
                className="home-diagram-caption",
                children=(
                    "Hydraulic states, water-quality transport and wall-attached biofilm "
                    "behaviour are treated as connected parts of the same network model."
                ),
            ),
        ],
    )
    


def create_layout():
    return html.Div(
        className="page home-page",
        children=[
            html.Section(
                className="home-hero",
                children=[
                    html.Div(
                        className="home-hero-copy",
                        children=[
                            dbc.Badge(
                                "Water distribution · Biofilm · Simulation",
                                color="info",
                                className="home-kicker",
                            ),
                            html.H1(
                                "Biofilm-aware simulation for drinking water networks",
                                className="home-title",
                            ),
                            html.P(
                                "This dashboard provides a visual shell for exploring hydraulic states, "
                                "transport behaviour and biofilm-related processes in EPANET-based "
                                "water distribution models.",
                                className="home-subtitle",
                            ),
                            html.P(
                                "The home screen is intentionally static: it is a project overview, "
                                "a visual entry point and a place for references, documentation and "
                                "research context.",
                                className="home-subtitle home-subtitle-secondary",
                            ),
                        ],
                    ),
                    _overview_diagram(),
                ],
            ),

            html.Section(
                className="home-section",
                children=[
                    html.Div(
                        className="home-section-header",
                        children=[
                            html.H2("What this project is about"),
                            html.P(
                                "A compact overview of the main modelling ideas behind the simulator."
                            ),
                        ],
                    ),
                    html.Div(
                        className="home-info-grid",
                        children=[
                            _info_card(
                                "💧",
                                "Hydraulic foundation",
                                "The network hydraulic state provides the baseline for velocity, flow direction, pressure and residence-time dependent analysis.",
                            ),
                            _info_card(
                                "🧪",
                                "Transport and reactions",
                                "Water quality behaviour can be studied through concentration transport, reaction assumptions and scenario comparison.",
                            ),
                            _info_card(
                                "🦠",
                                "Biofilm interaction",
                                "Biofilm-related processes are represented as wall-associated dynamics coupled to the hydraulic and quality state.",
                            ),
                        ],
                    ),
                ],
            ),

            html.Section(
                className="home-section home-two-column",
                children=[
                    dbc.Card(
                        className="app-card home-static-card",
                        children=[
                            dbc.CardHeader("Research context"),
                            dbc.CardBody(
                                children=[
                                    html.P(
                                        "The long-term goal is to connect network-scale hydraulic simulation "
                                        "with interpretable biological and water-quality indicators."
                                    ),
                                    html.P(
                                        "This page can later contain a short project description, methodology figure, "
                                        "publication references, validation notes, or screenshots from example scenarios."
                                    ),
                                    html.Div(
                                        className="home-highlight-box",
                                        children=[
                                            html.Div("Suggested figure slot", className="home-highlight-title"),
                                            html.P(
                                                "Ide jöhet később egy szép workflow ábra: EPANET input → hydraulic run "
                                                "→ quality transport → biofilm response → dashboard results."
                                            ),
                                        ],
                                    ),
                                ]
                            ),
                        ],
                    ),

                    dbc.Card(
                        className="app-card home-links-card",
                        children=[
                            dbc.CardHeader("External resources"),
                            dbc.CardBody(
                                children=[
                                    _external_link(
                                        "🧬",
                                        "STACI solver repository",
                                        "Placeholder link for the numerical solver or research backend.",
                                        "https://github.com/hoscsaba/staci",
                                    ),
                                    _external_link(
                                        "🏛️",
                                        "Department website",
                                        "Placeholder link for the university or department project page.",
                                        "https://www.hds.bme.hu/",
                                    ),
                                    _external_link(
                                        "📘",
                                        "Project documentation",
                                        "Placeholder link for technical notes, assumptions and usage examples.",
                                        "https://example.com/docs",
                                    ),
                                ]
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )