
import uuid
import datetime

def init_tree(initial_question):
    """Initializes the tree structure."""
    root_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "nodes": {
            root_id: {
                "id": root_id,
                "parent": None,
                "children": [],
                "summary": initial_question if initial_question else "[Main Topic]",
                "type": "root",
                "created_at": timestamp,
                "metadata": {}  # For storing full HTML, critiques, etc.
            }
        },
        "current": root_id,
        "pinned_items": [] # List of {"id": str, "text": str} or str
    }

def add_child(tree, parent_id, summary, node_type="standard", metadata=None):
    """Adds a child node to the tree."""
    child_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_node = {
        "id": child_id,
        "parent": parent_id,
        "children": [],
        "summary": summary,
        "type": node_type,
        "created_at": timestamp,
        "metadata": metadata or {}
    }
    
    tree["nodes"][child_id] = new_node
    if parent_id in tree["nodes"]:
        tree["nodes"][parent_id]["children"].append(child_id)
    
    return child_id

def get_node(tree, node_id):
    """Retrieves a node by ID."""
    if node_id in tree["nodes"]:
        return tree["nodes"][node_id]
    raise ValueError(f"Node {node_id} not found")

def get_current_node(tree):
    """Returns the current active node."""
    return get_node(tree, tree["current"])

def navigate_to_node(tree, node_id):
    """Updates the current node pointer with defensive logging."""
    # CLOUD GUARDRAIL: Strict Check
    # Prevents navigation if state is inconsistent (common in Streamlit Cloud reruns)
    from definitions import IS_CLOUD
    if IS_CLOUD:
        if node_id not in tree.get("nodes", {}):
            import logging
            logger = logging.getLogger(__name__)
            # In Cloud, we fallback to root or throw explicit error to prevent crash loop
            logger.critical(f"☁️ CLOUD UNSAFE NAV: Target {node_id} missing. Reverting to root.")
            # Fallback to current or root if possible, or just don't move pointer
            return

    if node_id in tree.get("nodes", {}):
        tree["current"] = node_id
    else:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ NAVIGATION ERROR: Attempted to navigate to non-existent node ID: {node_id}")
        raise ValueError(f"Node {node_id} not found in tree")

def get_nearest_html(tree, node_id):
    """Recursively finds the nearest HTML metadata up the tree."""
    from app import add_debug_log
    
    if node_id not in tree["nodes"]:
        return ""
    
    node = tree["nodes"][node_id]
    html = node.get("metadata", {}).get("html")
    if html:
        add_debug_log(f"🔍 NEAREST_HTML: Found content at {node_id} (len={len(html)})")
        return html
        
    parent_id = node.get("parent")
    if parent_id:
        add_debug_log(f"🔍 NEAREST_HTML: Node {node_id} empty. Climbing to parent {parent_id}")
        return get_nearest_html(tree, parent_id)
        
    add_debug_log(f"🔍 NEAREST_HTML: Reached root with no content.")
    return ""

def get_node_short_label(node):
    """
    Returns a short label for a node, prioritizing metadata label,
    then extracting a title/header, then truncating summary.
    """
    if not node:
        return "[Unknown]"

    # 1. Metadata Label
    if "label" in node.get("metadata", {}):
        return node["metadata"]["label"]

    summary = node.get("summary", "")
    if not summary:
        # Check if there is title in metadata
        if node.get("type") == "root":
             return "[Main Topic]"
        return "[Empty Idea]"

    # 2. Extract explicit Title:
    if "Title:" in summary:
        try:
            return summary.split("Title:")[1].split("\n")[0].strip(" *")
        except:
            pass

    # 3. HTML Header Extraction
    html = node.get("metadata", {}).get("html", "")
    if html:
        import re
        headers = re.findall(r"<h[1-6][^>]*>(.*?)</h[1-6]>", html)
        if headers:
            return headers[0].strip()

    # 4. Fallback: Truncate Summary
    # Take first sentence or first 50 chars
    first_line = summary.split("\n")[0].strip()
    if len(first_line) > 50:
        return first_line[:47] + "..."
    return first_line or "[Untitled Idea]"