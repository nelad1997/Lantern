from typing import Dict, List, Optional
import uuid

def create_node(
    summary: str,
    parent_id: Optional[str] = None, ) -> Dict:
    """
        Create a new tree node.

        A node represents a single idea, direction, or focus point in the tree.
        It does not insert the node into the tree structure; it only creates
        the node object itself.

        Args:
            summary (str):
                A short, canonical description of the idea or focus this node represents.
            parent_id (Optional[str]):
                The ID of the parent node. Use None if this node is the root.

        Returns:
            Dict:
                A dictionary representing the node, including its ID, parent,
                children list, and status.
        """
    return {
        "id": str(uuid.uuid4()),
        "summary": summary,        # canonical summary
        "parent": parent_id,       # None for root
        "children": [],            # list of node ids
        "status": "open"           # open | current | rejected
    }


def init_tree(root_summary: str) -> Dict:
    """
        Initialize a new tree with a single root node.

        This function creates the root node, sets it as the current node,
        and prepares the tree structure that will hold all future nodes.

        Args:
            root_summary (str):
                The initial summary representing the starting focus
                (e.g., a paragraph, section, or document-level idea).

        Returns:
            Dict:
                A tree dictionary containing:
                - 'nodes': a mapping of node_id to node objects
                - 'current': the node_id of the currently active node
        """
    root = create_node(summary=root_summary, parent_id=None)

    tree = {
        "nodes": {
            root["id"]: root
        },
        "current": root["id"]
    }

    tree["nodes"][root["id"]]["status"] = "current"

    return tree


def add_child(tree: Dict, parent_id: str, summary: str) -> str:
    """
        Add a new child node to the tree under a given parent node.

        This function creates a new node, inserts it into the tree,
        and links it as a child of the specified parent.

        Args:
            tree (Dict):
                The tree structure containing all nodes and the current pointer.
            parent_id (str):
                The ID of the parent node to which the child will be attached.
            summary (str):
                A short, canonical description of the new child node.

        Returns:
            str:
                The ID of the newly created child node.

        Raises:
            ValueError:
                If the specified parent_id does not exist in the tree.
        """
    if parent_id not in tree["nodes"]:
        raise ValueError("Parent node does not exist")

    child = create_node(summary=summary, parent_id=parent_id)

    tree["nodes"][child["id"]] = child
    tree["nodes"][parent_id]["children"].append(child["id"])

    return child["id"]


def set_current(tree: Dict, node_id: str):
    """
    Set the specified node as the current active node.

    This updates both the tree-level 'current' pointer and the status
    of the involved nodes.

    Args:
        tree (Dict):
            The tree structure.
        node_id (str):
            The ID of the node to become the current node.

    Raises:
        ValueError:
            If the specified node_id does not exist in the tree.
    """
    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    prev_id = tree["current"]
    tree["nodes"][prev_id]["status"] = "open"

    tree["current"] = node_id
    tree["nodes"][node_id]["status"] = "current"


def get_current_node(tree: Dict) -> Dict:
    """
    Retrieve the current active node from the tree.

    Args:
        tree (Dict):
            The tree structure.

    Returns:
        Dict:
            The current node object.
    """
    return tree["nodes"][tree["current"]]


def get_children(tree: Dict, node_id: Optional[str] = None) -> List[Dict]:
    """
    Retrieve child nodes for a given node.

    If no node_id is provided, children of the current node are returned.

    Args:
        tree (Dict):
            The tree structure.
        node_id (Optional[str]):
            The ID of the parent node. Defaults to the current node.

    Returns:
        List[Dict]:
            A list of child node objects.
    """
    if node_id is None:
        node_id = tree["current"]

    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    child_ids = tree["nodes"][node_id]["children"]
    return [tree["nodes"][cid] for cid in child_ids]


def is_root(tree: Dict, node_id: Optional[str] = None) -> bool:
    """
    Check whether a given node is the root node.

    A node is considered the root if it has no parent.

    Args:
        tree (Dict):
            The tree structure.
        node_id (Optional[str]):
            The ID of the node to check.
            If None, the current node is checked.

    Returns:
        bool:
            True if the node is the root, False otherwise.
    """
    if node_id is None:
        node_id = tree["current"]

    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    return tree["nodes"][node_id]["parent"] is None


def get_node(tree: Dict, node_id: str) -> Dict:
    """
    Retrieve a node by its ID.

    Args:
        tree (Dict):
            The tree structure.
        node_id (str):
            The ID of the node.

    Returns:
        Dict:
            The requested node.

    Raises:
        ValueError:
            If the node does not exist.
    """
    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    return tree["nodes"][node_id]

def has_children(tree: Dict, node_id: Optional[str] = None) -> bool:
    """
    Check whether a node has any child nodes.

    Args:
        tree (Dict):
            The tree structure.
        node_id (Optional[str]):
            The ID of the node to check. Defaults to the current node.

    Returns:
        bool:
            True if the node has children, False otherwise.
    """
    if node_id is None:
        node_id = tree["current"]

    return len(tree["nodes"][node_id]["children"]) > 0


def navigate_to_node(tree: Dict, node_id: str):
    """
    Navigate to an existing node without implying a decision.

    This function updates the current pointer to the specified node
    purely for navigation purposes. It does not create, reject,
    or modify nodes beyond updating focus.

    Args:
        tree (Dict):
            The tree structure.
        node_id (str):
            The ID of the node to navigate to.

    Raises:
        ValueError:
            If the specified node does not exist.
    """
    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    prev_id = tree["current"]
    tree["nodes"][prev_id]["status"] = "open"

    tree["current"] = node_id
    tree["nodes"][node_id]["status"] = "current"
