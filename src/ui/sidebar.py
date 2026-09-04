from __future__ import annotations
from dash import dcc, html


def nav_link(label: str, href: str, icon: str = ""):
    return dcc.Link(
        className="sidebar-link",
        href=href,
        children=[
            html.Span(icon, className="sidebar-link-icon"),
            html.Span(label)]
    )
    
def create_sidebar():
    sidebar = html.Aside(
        className="sidebar",
        children=[
            html.Div(
                className="sidebar-logo-block",
                children=[
                    html.Img(
                        src="/assets/images/logo_gpt2.png",
                        className="sidebar-logo-image",
                        alt="STACI EPS Dashboard"
                    )
                ]
            ),
            nav_link("Home", "/", "📊"),
            html.Hr(className="sidebar-separator"),
            html.Div("Water Network", className="sidebar-section-title"),
            nav_link("Load Model", "/network/load", "📁"),
            nav_link("Partitioning", "/network/partitioning", "🧩"),
            html.Div("Analysis", className="sidebar-section-title sidebar-section-spaced"),
            nav_link("Hydraulic", "/analysis/hydraulic", "💧"),
            nav_link("Quality", "/analysis/quality", "🧪"),
            nav_link("Biofilm", "/analysis/biofilm", "🦠"),
            html.Hr(className="sidebar-separator"),
            html.Div(
                className="sidebar-footer",
                children="STACI UI · Hydraulic simulation interface\n BME · Department of Hydrodynamic Systems",
            ),  
        ]
    )
    
    return sidebar