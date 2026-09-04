from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from dataclasses import dataclass
import shutil
import uuid


from src.staci.split import write_split_settings, run_staci_split
from src.config import RUN_ROOT


@dataclass
class ParsedMembership:
    n_nodes: int
    node_community: Dict[str, int]
    n_community_members: Dict[int, int]

    @property
    def n_communities(self) -> int:
        return len(set(self.node_community.values()))
    
def parse_membership(path: Path) -> ParsedMembership:
    if not path.is_file():
        raise FileNotFoundError(
            f"Membership file not found: {path}"
        )

    n_nodes: int | None = None
    node_community: dict[str, int] = {}
    n_community_members: dict[int, int] = {} 

    lines = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        # Example:
        # n_nodes : 1605
        if line.startswith("n_nodes"):
            _, value = line.split(":", maxsplit=1)
            n_nodes = int(value.strip())
            continue

        # Example:
        # #0; J345; J346; J347; ...
        if not line.startswith("#"):
            continue

        parts = [
            part.strip()
            for part in line.split(";")
            if part.strip()
        ]

        if not parts:
            continue

        community_id = int(parts[0][1:])
        
        n_valid_members = 0
        for node_id in parts[1:]:
            if node_id in node_community:
                raise ValueError(
                    f"Node '{node_id}' appears in multiple communities."
                )

            node_community[node_id] = community_id
            n_valid_members += 1
        
        n_community_members[community_id] = n_valid_members  

    if n_nodes is None:
        raise ValueError(
            f"Could not find n_nodes in membership file: {path}"
        )

    if len(node_community) != n_nodes:
        raise ValueError(
            "Membership node count mismatch: "
            f"expected {n_nodes}, parsed {len(node_community)}."
        )

    return ParsedMembership(
        n_nodes=n_nodes,
        node_community=node_community,
        n_community_members=n_community_members
    )
    

def call_staci_split_service(
    inp_path: Path | str,
    *,
    model_id: str,
    optimizer_settings: Dict[str, Any] | None = None,
    seed: int = 12345,
) -> Dict[str, Any]:
    
    inp_path = Path(inp_path)
    if not inp_path.exists():
        raise FileNotFoundError(f"INP file does not exist: {inp_path}")
    
    run_id = uuid.uuid4().hex[:12]
    run_dir = Path(RUN_ROOT) / "partition" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Keep the uploaded/original model untouched.
    run_inp = run_dir / "model.inp"
    shutil.copy2(inp_path, run_inp)
    
    settings_path = run_dir / "staci_split_settings.xml"
    
    write_split_settings(
        settings_path,
        inp_path=run_inp,
        overrides=optimizer_settings
    )
    
    split_results = run_staci_split(
        run_inp,
        settings_path,
        seed=seed
    )
    
    if not split_results.success or not split_results.membership_path:
        raise RuntimeError(
            f"STACI_SPLIT did not complete successfully "
            f"(return code {split_results.returncode}). "
            f"See {split_results.stderr_path}"
        )
    
    membership = parse_membership(split_results.membership_path)
    
    return {
        "success": True,
        "run_id": run_id,
        "model_id": model_id,
        "n_nodes": membership.n_nodes,
        "n_communities": membership.n_communities,
        "n_community_members": membership.n_community_members,
        "node_community": membership.node_community,
    }
        
    
    
    