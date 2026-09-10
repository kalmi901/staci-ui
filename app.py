import logging
import dash_bootstrap_components as dbc
from dash import Dash

from src.ui.app_shell import create_app_shell
from src.ui.callbacks import register_callbacks
from src.config import (
    DASH_DEBUG,
    APP_URL_PREFIX,
)

logging.basicConfig(
    level=logging.DEBUG if DASH_DEBUG else logging.INFO,
    format=(
        "%(asctime)s | %(levelname)-8s | "
        "%(name)s | %(message)s")
)

def create_app() -> Dash:
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        url_base_pathname=APP_URL_PREFIX,
        update_title=""
    )
    
    app.title = "STACI Dashboard"
    app.layout = create_app_shell()
    register_callbacks(app)
    return app

app = create_app()
server = app.server
