from src.ui.callbacks.routing import register_routing_callbacks
from src.ui.callbacks.network_callbacks import register_network_callbacks

def register_callbacks(app):
    register_routing_callbacks(app)
    register_network_callbacks(app)