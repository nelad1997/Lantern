#
# from typing import Dict, List, Optional, Any
# import uuid
#
# def create_node(
#     summary: str,
#     parent_id: Optional[str] = None,
#     metadata: Optional[Dict[str, Any]] = None
# ) -> Dict:
#     """
#     Create a new tree node with optional metadata.
#     """
#     return {
#         "id": str(uuid.uuid4()),
#         "summary": summary,
#         "parent": parent_id,
#         "children": [],
#         "status": "open",
#         "metadata": metadata or {}  # שדה חדש לגמישות
#     }
#
#
# def init_tree(root_summary: str) -> Dict:
#     root = create_node(summary=root_summary, parent_id=None)
#
#     tree = {
#         "nodes": {
#             root["id"]: root
#         },
#         "current": root["id"]
#     }
#
#     tree["nodes"][root["id"]]["status"] = "current"
#     return tree
#
#
# def add_child(tree: Dict, parent_id: str, summary: str, metadata: Optional[Dict] = None) -> str:
#     """
#     Add a new child node, potentially with metadata.
#     """
#     if parent_id not in tree["nodes"]:
#         raise ValueError("Parent node does not exist")
#
#     child = create_node(summary=summary, parent_id=parent_id, metadata=metadata)
#
#     tree["nodes"][child["id"]] = child
#     tree["nodes"][parent_id]["children"].append(child["id"])
#
#     return child["id"]
#
#
# def set_current(tree: Dict, node_id: str):
#     if node_id not in tree["nodes"]:
#         raise ValueError("Node does not exist")
#
#     prev_id = tree["current"]
#     tree["nodes"][prev_id]["status"] = "open"
#
#     tree["current"] = node_id
#     tree["nodes"][node_id]["status"] = "current"
#
#
# def get_current_node(tree: Dict) -> Dict:
#     return tree["nodes"][tree["current"]]
#
#
# def get_children(tree: Dict, node_id: Optional[str] = None) -> List[Dict]:
#     if node_id is None:
#         node_id = tree["current"]
#
#     if node_id not in tree["nodes"]:
#         raise ValueError("Node does not exist")
#
#     child_ids = tree["nodes"][node_id]["children"]
#     return [tree["nodes"][cid] for cid in child_ids]
#
#
# def is_root(tree: Dict, node_id: Optional[str] = None) -> bool:
#     if node_id is None:
#         node_id = tree["current"]
#
#     if node_id not in tree["nodes"]:
#         raise ValueError("Node does not exist")
#
#     return tree["nodes"][node_id]["parent"] is None
#
#
# def get_node(tree: Dict, node_id: str) -> Dict:
#     if node_id not in tree["nodes"]:
#         raise ValueError("Node does not exist")
#
#     return tree["nodes"][node_id]
#
#
# def has_children(tree: Dict, node_id: Optional[str] = None) -> bool:
#     if node_id is None:
#         node_id = tree["current"]
#
#     return len(tree["nodes"][node_id]["children"]) > 0
#
#
# def navigate_to_node(tree: Dict, node_id: str):
#     if node_id not in tree["nodes"]:
#         raise ValueError("Node does not exist")
#
#     prev_id = tree["current"]
#     tree["nodes"][prev_id]["status"] = "open"
#
#     tree["current"] = node_id
#     tree["nodes"][node_id]["status"] = "current"

from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime


def get_timestamp():
    """Returns current time in HH:MM format"""
    return datetime.now().strftime("%H:%M")


def create_node(
        summary: str,
        parent_id: Optional[str] = None,
        node_type: str = "standard",
        metadata: Optional[Dict[str, Any]] = None
) -> Dict:
    """
    Create a new tree node with metadata and timestamp.
    node_type options: 'root', 'user', 'ai_diverge', 'ai_critique'
    """
    return {
        "id": str(uuid.uuid4()),
        "summary": summary,
        "parent": parent_id,
        "children": [],
        "status": "open",
        "type": node_type,  # שדה חדש לזיהוי סוג הצומת
        "created_at": get_timestamp(),  # שדה חדש לזמן
        "metadata": metadata or {}
    }


def init_tree(root_summary: str) -> Dict:
    """Initialize the tree with a Root node"""
    root = create_node(
        summary=root_summary if root_summary else "Start writing here...",
        parent_id=None,
        node_type="root"
    )

    tree = {
        "nodes": {
            root["id"]: root
        },
        "current": root["id"]
    }

    tree["nodes"][root["id"]]["status"] = "current"
    return tree


def add_child(
        tree: Dict,
        parent_id: str,
        summary: str,
        node_type: str = "standard",
        metadata: Optional[Dict] = None
) -> str:
    """
    Add a new child node to the tree.
    """
    if parent_id not in tree["nodes"]:
        raise ValueError("Parent node does not exist")

    child = create_node(
        summary=summary,
        parent_id=parent_id,
        node_type=node_type,
        metadata=metadata
    )

    tree["nodes"][child["id"]] = child
    tree["nodes"][parent_id]["children"].append(child["id"])

    return child["id"]


def set_current(tree: Dict, node_id: str):
    """Update the cursor (current active node)"""
    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    # Update previous current status
    prev_id = tree["current"]
    if prev_id in tree["nodes"]:
        tree["nodes"][prev_id]["status"] = "open"

    # Set new current
    tree["current"] = node_id
    tree["nodes"][node_id]["status"] = "current"


def navigate_to_node(tree: Dict, node_id: str):
    """Wrapper for set_current to be used in UI callbacks"""
    set_current(tree, node_id)


# --- Getters / Helpers ---

def get_current_node(tree: Dict) -> Dict:
    return tree["nodes"][tree["current"]]


def get_node(tree: Dict, node_id: str) -> Dict:
    if node_id not in tree["nodes"]:
        raise ValueError(f"Node {node_id} does not exist")
    return tree["nodes"][node_id]


def get_children(tree: Dict, node_id: Optional[str] = None) -> List[Dict]:
    """Get full node objects for all children of a node"""
    if node_id is None:
        node_id = tree["current"]

    if node_id not in tree["nodes"]:
        return []

    child_ids = tree["nodes"][node_id]["children"]
    return [tree["nodes"][cid] for cid in child_ids]


def get_ancestry(tree: Dict, node_id: str) -> List[Dict]:
    """
    Returns a list of nodes from Root down to the specified node_id.
    Useful for visualizing the active path.
    """
    path = []
    curr = node_id

    while curr:
        node = get_node(tree, curr)
        path.append(node)
        curr = node["parent"]

    return list(reversed(path))
