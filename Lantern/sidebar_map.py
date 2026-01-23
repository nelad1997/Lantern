import streamlit as st
import graphviz
from tree import get_node, get_children, navigate_to_node, init_tree

def truncate(text, length=20):
    return text[:length] + "..." if len(text) > length else text

def get_depth(tree, node_id):
    depth = 0
    curr = tree["nodes"].get(node_id)
    while curr and curr["parent"]:
        depth += 1
        curr = tree["nodes"].get(curr["parent"])
    return depth

def get_node_color(node, current_id, banned_ids):
    if node["id"] == current_id:
        return "#7c3aed", "white" # Purple-600, White text
    if node["id"] in banned_ids:
        return "#f1f5f9", "#94a3b8" # Slate-100, Slate-400
    if node["type"] == "root":
        return "#ecfdf5", "#047857" # Emerald-50, Emerald-700
    return "#ffffff", "#334155" # White, Slate-700

def format_for_pin(text):
    """Helper to format text nicely for Pinned Context (bold title)."""
    if "Title:" in text:
        if "Explanation:" in text:
             parts = text.replace("Title:", "").split("Explanation:", 1)
        else:
             parts = text.replace("Title:", "").split("\n", 1)
        
        if len(parts) >= 2:
            return f"**{parts[0].strip(' *')}**\n\n{parts[1].strip()}"
    return text

def render_sidebar_map(tree):
    """
    Renders the tree visualization using Graphviz and navigation buttons.
    """
    st.sidebar.subheader("🗺️ Thought Tree")

    # 1. Graphviz Visualization
    graph = graphviz.Digraph()
    graph.attr(rankdir='TB', size='3,5') # Top-to-Bottom, constrained width
    graph.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', fontsize='10')
    graph.attr('edge', color='#cbd5e1')

    # Traverse and build graph (BFS/DFS)
    # To avoid huge graphs, we might limit depth or focus on active branch? 
    # For now, render full tree (assuming reasonably small sessions)
    
    current_id = tree["current"]
    banned_ids = st.session_state.get("banned_ideas", [])
    
    for node_id, node in tree["nodes"].items():
        # Skip completely if it's a "deep" banned node? No, show them as pruned.
        
        fill_color, font_color = get_node_color(node, current_id, banned_ids)
        border_color = "#7c3aed" if node_id == current_id else "#e2e8f0"
        penwidth = "2" if node_id == current_id else "1"
        
        # Prefer 'label' from metadata (if available) for the tree node text
        raw_label = node.get("metadata", {}).get("label", node["summary"])
        label = truncate(raw_label, 15)
        tooltip = raw_label
        
        graph.node(
            node_id, 
            label=label, 
            fillcolor=fill_color, 
            fontcolor=font_color, 
            color=border_color, 
            penwidth=penwidth, 
            tooltip=tooltip,
            URL=f"?node_id={node_id}" # Directly trigger interactive navigation via query param
        )
        
        if node["parent"]:
             graph.edge(node["parent"], node_id)

    st.sidebar.graphviz_chart(graph, use_container_width=True)

    # 4. Reset Tool
    st.sidebar.divider()
    st.sidebar.caption("Reset Workspace", help="Completely wipe the tree and context to start a new session.")
    if st.sidebar.button("🗑️ Reset Full Tree", help="Permanently delete all branches and start a new session from scratch.", use_container_width=True):
        # Capture current content to keep it in the new root
        current_node = tree["nodes"][tree["current"]]
        curr_summary = current_node.get("summary", "")
        curr_metadata = current_node.get("metadata", {}).copy()
        
        st.session_state.tree = init_tree(curr_summary, curr_metadata)
        st.session_state.pinned_context = []
        st.session_state.selected_paths = []
        st.session_state.banned_ideas = []
        st.session_state.pop("current_critiques", None)
        st.session_state.pop("comparison_data", None)
        st.session_state.pop("last_refine_diff", None)
        st.session_state.pop("editor_html", None)
        # Force editor to refresh (if using the versioning trick)
        if "editor_version" in st.session_state:
            st.session_state.editor_version += 1
        st.rerun()
