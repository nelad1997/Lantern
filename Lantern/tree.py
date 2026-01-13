
from typing import Dict, List, Optional, Any
import uuid

def create_node(
    summary: str,
    parent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict:
    """
    Create a new tree node with optional metadata.
    """
    return {
        "id": str(uuid.uuid4()),
        "summary": summary,
        "parent": parent_id,
        "children": [],
        "status": "open",
        "metadata": metadata or {}  # שדה חדש לגמישות
    }


def init_tree(root_summary: str) -> Dict:
    root = create_node(summary=root_summary, parent_id=None)

    tree = {
        "nodes": {
            root["id"]: root
        },
        "current": root["id"]
    }

    tree["nodes"][root["id"]]["status"] = "current"
    return tree


def add_child(tree: Dict, parent_id: str, summary: str, metadata: Optional[Dict] = None) -> str:
    """
    Add a new child node, potentially with metadata.
    """
    if parent_id not in tree["nodes"]:
        raise ValueError("Parent node does not exist")

    child = create_node(summary=summary, parent_id=parent_id, metadata=metadata)

    tree["nodes"][child["id"]] = child
    tree["nodes"][parent_id]["children"].append(child["id"])

    return child["id"]


def set_current(tree: Dict, node_id: str):
    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    prev_id = tree["current"]
    tree["nodes"][prev_id]["status"] = "open"

    tree["current"] = node_id
    tree["nodes"][node_id]["status"] = "current"


def get_current_node(tree: Dict) -> Dict:
    return tree["nodes"][tree["current"]]


def get_children(tree: Dict, node_id: Optional[str] = None) -> List[Dict]:
    if node_id is None:
        node_id = tree["current"]

    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    child_ids = tree["nodes"][node_id]["children"]
    return [tree["nodes"][cid] for cid in child_ids]


def is_root(tree: Dict, node_id: Optional[str] = None) -> bool:
    if node_id is None:
        node_id = tree["current"]

    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    return tree["nodes"][node_id]["parent"] is None


def get_node(tree: Dict, node_id: str) -> Dict:
    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    return tree["nodes"][node_id]


def has_children(tree: Dict, node_id: Optional[str] = None) -> bool:
    if node_id is None:
        node_id = tree["current"]

    return len(tree["nodes"][node_id]["children"]) > 0


def navigate_to_node(tree: Dict, node_id: str):
    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    prev_id = tree["current"]
    tree["nodes"][prev_id]["status"] = "open"

    tree["current"] = node_id
    tree["nodes"][node_id]["status"] = "current"
