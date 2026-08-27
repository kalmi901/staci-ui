import os
import dash_bootstrap_components as dbc
from dash import Dash
from dash_auth import BasicAuth

from src.ui.app_shell import create_app_shell
from src.ui.callbacks import register_callbacks

def create_app() -> Dash:
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )
    
    BasicAuth(
        app,
        {
            os.getenv("DASH_USER", "staci") : 
                os.getenv("DASH_PASSWORD", "staci")
        }, secret_key = os.getenv(
            "DASH_AUTH_SECRET",
            "dev-secret-change-me"
        )
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
        port=int(os.getenv("PORT", "8050")),
        debug=os.getenv("DASH_DEBUG", "0") == "0",
    )