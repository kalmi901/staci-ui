from src.ui.callbacks.routing import register_routing_callbacks
from src.ui.callbacks.network_callbacks import register_network_callbacks
from src.ui.callbacks.partitioning_callbacks import register_partitioning_callbacks
from src.ui.callbacks.hydraulic_callbacks import register_hydraulic_callbacks

def register_callbacks(app):
    register_routing_callbacks(app)
    register_network_callbacks(app)
    register_partitioning_callbacks(app)
    register_hydraulic_callbacks(app)