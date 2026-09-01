from __future__ import annotations
import wntr
from pathlib import Path
from typing import Union, Dict, Any, List


def _as_wn(inp_or_wn) -> wntr.network.WaterNetworkModel:
    if isinstance(inp_or_wn, wntr.network.WaterNetworkModel):
        return inp_or_wn
    
    try:
        wn = wntr.network.WaterNetworkModel(str(inp_or_wn))
        return wn
    except Exception as e:
        raise ValueError(f"Could not load water network model: {e}")
    
    
def read_model_summary(inp_or_wn: Union[Path, wntr.network.WaterNetworkModel]) -> Dict[str, Any]:
    wn = _as_wn(inp_or_wn)
    return wn.describe(level=1)


def read_water_network_model(
    inp_or_wn: Union[Path, wntr.network.WaterNetworkModel]) -> Dict[str, Any]:
    wn = _as_wn(inp_or_wn)
    
    # Read Nodes:
    node_id: List[str] = []
    node_type: List[str] = []
    node_x: List[float | None] = []
    node_y: List[float | None] = []
    node_elevation: List[float] = []
    node_demand: List = []
    
    # Read Pipes
    link_id: List[str] = []
    link_type: List[str] = []
    link_start_node: List[str | None] = []
    link_end_node: List[str | None] = []
    link_start_idx: List[int | None] = []
    link_end_idx: List[int | None] = []
    link_length: List[float] = []
    link_diameter: List[float] = []
    link_roughness: List[float] = []
    
    
    # TODO -> decompose to junctions, tanks and reservoirs
    for nid, node in wn.nodes():
        # Node ID & Tpye
        node_id.append(nid)
        node_type.append(node.node_type)
        
        # Coordinates
        x, y = getattr(node, "coordinates", (None, None))
        node_x.append(x)
        node_y.append(y)
        
        # Elevation (base-head for reservoir)
        if isinstance(node, wntr.network.Reservoir):
            elevation = getattr(node, "base_head", 0)
        else:
            elevation = getattr(node, "elevation", 0)
        
        node_elevation.append(elevation)
        
        base_demand = 0.0
        if isinstance(node, wntr.network.elements.Junction):
            for pattern in node.demand_timeseries_list:
                base_demand += pattern.base_value
        node_demand.append(base_demand * 3600)
    
    node_index = {nid: i for i, nid in enumerate(node_id)}
    
    for lid, link in wn.links():
        start_node = link.start_node_name
        end_node = link.end_node_name
        # Ha valamiért nincs node hozzá, kihagyjuk de bugokat ki kell innen gyomlálni majd, elvileg helyes hálózatban ilyen nincs
        if start_node not in node_index or end_node not in node_index:
            continue
        
        link_id.append(lid)
        link_type.append(link.link_type)
        link_start_node.append(start_node)
        link_end_node.append(end_node)
        link_start_idx.append(node_index[start_node])
        link_end_idx.append(node_index[end_node])
        link_length.append(getattr(link, "length", 0))
        link_diameter.append(getattr(link, "diameter", 0))
        link_roughness.append(getattr(link, "roughness", 0))     
        
    valid_diameter = [x for x in link_diameter if x != 0]
    valid_length   = [x for x in link_length if x != 0]
    valid_roughness= [x for x in link_roughness if x != 0]    
    
    return {
        "nodes": {
            "id"            : node_id,
            "type"          : node_type,
            "x"             : node_x,
            "y"             : node_y,
            "elevation"     : node_elevation,
            "demand"        : node_demand
        },
        "links": {
            "id"            : link_id,
            "type"          : link_type,
            "start_node"    : link_start_node,
            "end_node"      : link_end_node,
            "start_index"   : link_start_idx,
            "end_index"     : link_end_idx,
            "length"        : link_length,
            "diameter"      : link_diameter,
            "roughness"     : link_roughness 
        },
        "ranges": {
            "elevation" : {"unit" : "m", "min": min(node_elevation),"max": max(node_elevation)},
            "demand"    : {"unit": "m^3/h", "min": min(node_demand),"max": max(node_demand)},
            "diameter"  : {"unit": "m", "min": min(valid_diameter), "max": max(valid_diameter)},
            "length"    : {"unit": "m", "min": min(valid_length),   "max": max(valid_length)},
            "roughness" : {"unit": None, "min" : min(valid_roughness),"max" : max(valid_roughness)}
        }}
    