import uuid
import datetime
import os
import json
import tempfile
import logging
import streamlit as st

# Ensure sessions directory exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

logger = logging.getLogger(__name__)

def get_session_id():
    """Retrieves a stable session ID from st.session_state."""
    if "stable_session_id" not in st.session_state:
        st.session_state.stable_session_id = str(uuid.uuid4())[:8]
        logger.info(f"✨ NEW SESSION INIT: {st.session_state.stable_session_id}")
    return st.session_state.stable_session_id

def save_tree(tree):
    """Saves the tree to disk safely with all persistent state."""
    try:
        sid = get_session_id()
        filename = f"tree_{sid}.json"
        filepath = os.path.join(SESSIONS_DIR, filename)
        
        # Consistent payload with ALL persistent state
        data = {
            "nodes": tree["nodes"],
            "current": tree["current"],
            "pinned_items": tree.get("pinned_items", []),
            "banned_ideas": tree.get("banned_ideas", []),
            "dismissed_suggestions": list(tree.get("dismissed_suggestions", [])),
            "bulletproof_history": list(tree.get("bulletproof_history", [])),
            "current_critiques": tree.get("current_critiques", []),
            "pending_refine_edits": tree.get("pending_refine_edits", []),
            "timestamp": str(datetime.datetime.now())
        }
        
        # Write to temp file
        fd, tmp_path = tempfile.mkstemp(dir=SESSIONS_DIR, suffix=".tmp", text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                json.dump(data, tmp, indent=2)
            
            # Atomic replace (robust on Windows for existing files)
            os.replace(tmp_path, filepath)
        except Exception as e:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            raise e
            
    except Exception as e:
        logger.error(f"❌ Save Failed: {e}")

def load_tree():
    """Loads tree from disk, with Sticky Recovery for lost sessions."""
    # 1. Try loading with current Session ID
    sid = get_session_id()
    filename = f"tree_{sid}.json"
    filepath = os.path.join(SESSIONS_DIR, filename)

    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"📂 Loaded session {sid}")
            return _parse_tree_data(data)
        except Exception as e:
            logger.error(f"❌ Corrupt session file {filename}: {e}")

    # 2. Sticky Recovery: If current ID has no file, find the most recent session
    try:
        import glob
        pattern = os.path.join(SESSIONS_DIR, "tree_*.json")
        files = glob.glob(pattern)
        
        if files:
            # Find newest file
            latest_file = max(files, key=os.path.getmtime)
            
            # Load it
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # RECOVER THE ID from filename "tree_{uuid}.json"
            recovered_id = os.path.basename(latest_file).replace("tree_", "").replace(".json", "")
            
            # UPDATE STATE to match this recovered session
            st.session_state.stable_session_id = recovered_id
            logger.info(f"♻️ STICKY RECOVERY: Restored last session {recovered_id}")
            
            return _parse_tree_data(data)
            
    except Exception as e:
        logger.error(f"❌ Sticky Recovery Failed: {e}")

    return None

def _parse_tree_data(data):
    """Helper to ensure consistent data structure with all fields."""
    return {
        "nodes": data["nodes"],
        "current": data["current"],
        "pinned_items": data.get("pinned_items", []),
        "banned_ideas": data.get("banned_ideas", []),
        "dismissed_suggestions": set(data.get("dismissed_suggestions", [])),
        "bulletproof_history": set(data.get("bulletproof_history", [])),
        "current_critiques": data.get("current_critiques", []),
        "pending_refine_edits": data.get("pending_refine_edits", [])
    }

def init_tree(initial_question):
    """Initializes the tree structure with all state fields."""
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
                "metadata": {} 
            }
        },
        "current": root_id,
        "pinned_items": [],
        "banned_ideas": [],
        "dismissed_suggestions": set(),
        "bulletproof_history": set(),
        "current_critiques": [],
        "pending_refine_edits": []
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
    
    # Auto-save on modification
    save_tree(tree)
    
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
    from definitions import IS_CLOUD
    if IS_CLOUD:
        if node_id not in tree.get("nodes", {}):
            import logging
            logger = logging.getLogger(__name__)
            logger.critical(f"☁️ CLOUD UNSAFE NAV: Target {node_id} missing. Reverting to root.")
            return

    if node_id in tree.get("nodes", {}):
        tree["current"] = node_id
        save_tree(tree)
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

    if "label" in node.get("metadata", {}):
        return node["metadata"]["label"]

    summary = node.get("summary", "")
    if not summary:
        if node.get("type") == "root":
             return "[Main Topic]"
        return "[Empty Idea]"

    if "Title:" in summary:
        try:
            return summary.split("Title:")[1].split("\n")[0].strip(" *")
        except:
            pass

    html = node.get("metadata", {}).get("html", "")
    if html:
        import re
        headers = re.findall(r"<h[1-6][^>]*>(.*?)</h[1-6]>", html)
        if headers:
            return headers[0].strip()

    first_line = summary.split("\n")[0].strip()
    if len(first_line) > 50:
        return first_line[:47] + "..."
    return first_line or "[Untitled Idea]"