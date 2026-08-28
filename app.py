import os
import dash_bootstrap_components as dbc
from dash import Dash
from dash_auth import BasicAuth

from src.ui.app_shell import create_app_shell
from src.ui.callbacks import register_callbacks
from src.config import (
    DASH_AUTH_SECRET,
    DASH_DEBUG,
    DASH_USER,
    DASH_PASSWORD,
    PORT
)

def create_app() -> Dash:
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )
    
    BasicAuth(
        app,
        {DASH_USER: DASH_PASSWORD}, 
        secret_key = DASH_AUTH_SECRET
    )
    
    app.title = "STACI Dashboard"
    app.layout = create_app_shell()
    register_callbacks(app)
    return app

app = create_app()
server = app.server

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=DASH_DEBUG,
    )