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
    יוצר צומת חדש בעץ הכולל מטא-דאטה וחותמת זמן.
    node_type: 'root', 'user', 'ai_diverge', 'ai_critique', 'refine'
    """
    return {
        "id": str(uuid.uuid4()),
        "summary": summary,
        "parent": parent_id,
        "children": [],
        "status": "open",
        "type": node_type,  # סיווג סוג המחשבה לצורך ויזואליזציה במפה
        "created_at": get_timestamp(),
        "metadata": metadata or {
            "critiques": []  # אתחול רשימת ביקורות עבור כל צומת
        }
    }


def init_tree(root_summary: str) -> Dict:
    """אתחול העץ עם צומת שורש (Root) [cite: 10]"""
    root = create_node(
        summary=root_summary if root_summary else "",
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
    """הוספת צומת בן חדש לעץ (הסתעפות רעיונית) [cite: 27, 138]"""
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


def update_node_metadata(tree: Dict, node_id: str, key: str, value: Any):
    """
    עדכון ה-Metadata של צומת קיים.
    משמש לשמירת ביקורות (Critiques) מה-Devil's Advocate[cite: 15, 144].
    """
    if node_id not in tree["nodes"]:
        raise ValueError(f"Node {node_id} does not exist")

    node = tree["nodes"][node_id]

    if key == "critiques":
        if "critiques" not in node["metadata"] or not isinstance(node["metadata"]["critiques"], list):
            node["metadata"]["critiques"] = []
        node["metadata"]["critiques"].append(value)
    else:
        node["metadata"][key] = value


def set_current(tree: Dict, node_id: str):
    """עדכון המיקום הנוכחי בעץ (Cursor)"""
    if node_id not in tree["nodes"]:
        raise ValueError("Node does not exist")

    prev_id = tree["current"]
    if prev_id in tree["nodes"]:
        tree["nodes"][prev_id]["status"] = "open"

    tree["current"] = node_id
    tree["nodes"][node_id]["status"] = "current"


def navigate_to_node(tree: Dict, node_id: str):
    """
    פונקציית עזר לניווט המופעלת מהממשק.
    מאפשרת למשתמש לעבור בין נתיבי חשיבה מקבילים[cite: 29, 32].
    """
    set_current(tree, node_id)


# --- Getters / Helpers ---

def get_current_node(tree: Dict) -> Dict:
    return tree["nodes"][tree["current"]]


def get_node(tree: Dict, node_id: str) -> Dict:
    if node_id not in tree["nodes"]:
        raise ValueError(f"Node {node_id} does not exist")
    return tree["nodes"][node_id]


def get_children(tree: Dict, node_id: Optional[str] = None) -> List[Dict]:
    """שליפת כל הבנים של צומת מסוים [cite: 137]"""
    if node_id is None:
        node_id = tree["current"]

    if node_id not in tree["nodes"]:
        return []

    child_ids = tree["nodes"][node_id]["children"]
    return [tree["nodes"][cid] for cid in child_ids]