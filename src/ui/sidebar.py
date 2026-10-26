from __future__ import annotations
from dash import dcc, html
from src.ui.paths import app_path
from collections.abc import Sequence

WORDPRESS_HOME_URL = "https://hydroreact.org/"

NavItem = tuple[str, str, str]


WATER_NETWORK_LINKS: tuple[NavItem, ...] = (
    ("Load Model", "/network/load","📁"),
)

ANALYSIS_LINKS: tuple[NavItem, ...] = (
    ("Hydraulic", "/analysis/hydraulic", "💧"),
    ("Partitioning", "/analysis/partitioning", "🧩"),
    ("Flushing", "/analysis/flushing", "🚿"),
)


def internal_nav_link(label: str, href: str, icon: str = ""):
    return dcc.Link(
        className="sidebar-link",
        href=app_path(href),
        children=[
            html.Span(icon, className="sidebar-link-icon"),
            html.Span(label)]
    )


def external_nav_link(
    label: str,
    href: str,
    icon: str = "",
):
    return html.A(
        className="sidebar-link",
        href=href,
        target="_top",
        children=[
            html.Span(
                icon,
                className="sidebar-link-icon",
            ),
            html.Span(label),
        ],
    )


def navigation_section(
    title: str,
    links: Sequence[NavItem],
    *,
    spaced: bool = False,
):
    title_class = "sidebar-section-title"

    if spaced:
        title_class += " sidebar-section-spaced"

    return [
        html.Div(
            title,
            className=title_class,
        ),
        *[
            internal_nav_link(
                label,
                href,
                icon,
            )
            for label, href, icon in links
        ],
    ]


def create_sidebar():
    return html.Aside(
        className="sidebar",
        children=[
            external_nav_link("Home", WORDPRESS_HOME_URL,"🏠"),
            html.Hr(className="sidebar-separator"),
            *navigation_section("Water Network", WATER_NETWORK_LINKS),
            *navigation_section("Analysis", ANALYSIS_LINKS, spaced=True),
            html.Hr(className="sidebar-separator"),
            html.Div(className="sidebar-footer",
                children=(
                    "STACI UI · Hydraulic simulation interface"
                    "\nBME · Department of Hydrodynamic Systems"
                ),
            ),
        ],
    )
