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
        
        graph.node(node_id, label=label, fillcolor=fill_color, fontcolor=font_color, color=border_color, penwidth=penwidth, tooltip=tooltip)
        
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
        # Force editor to refresh (if using the versioning trick)
        if "editor_version" in st.session_state:
            st.session_state.editor_version += 1
        st.rerun()

    # 2. Navigation Tools
    st.sidebar.divider()
    st.sidebar.subheader("📍 Navigation", help="Navigate through your thought history. Click on previous nodes to return to them.")
    
    # Show Ancestors (Path to Root)
    st.sidebar.caption("Current Path", help="The sequence of ideas leading to your current state.")
    
    path = []
    temp_id = current_id
    while temp_id:
        node = get_node(tree, temp_id)
        path.append(node)
        temp_id = node["parent"]
    path.reverse()
    
    for node in path:
        is_active = (node["id"] == current_id)
        
        # Determine the label: Use descriptive label if available, otherwise truncate summary
        label_text = node.get("metadata", {}).get("label")
        if not label_text:
            nav_text = node['summary']
            if not nav_text or not nav_text.strip():
                nav_text = "Start" if node["type"] == "root" else "Untitled Idea"
            label_text = truncate(nav_text, 25)
            
        label = f"{'🟣' if is_active else '⚪'} {label_text}"
        
        # Concise Tooltip: Summarize the idea instead of showing full raw text
        # If it's a long text, we skip the middle part for the tooltip or use a "General Explanation"
        node_summary = node.get("summary", "")
        clean_tooltip = node_summary[:100] + "..." if len(node_summary) > 100 else node_summary
        
        if st.sidebar.button(label, key=f"nav_btn_{node['id']}", disabled=is_active, help=f"Return to: {clean_tooltip}"):
            # Root Navigation = Reset Context
            if node["type"] == "root":
                st.session_state.pinned_context = []
                st.session_state.selected_paths = []
                st.session_state.banned_ideas = []
            
            navigate_to_node(tree, node['id'])
            if "editor_version" in st.session_state:
                st.session_state.editor_version += 1
            st.rerun()

    # Show Siblings (Alternatives)
    current_node = get_node(tree, current_id)
    if current_node["parent"]:
        siblings = get_children(tree, current_node["parent"])
        alternatives = [s for s in siblings if s["id"] != current_id and s["id"] not in banned_ids]
        
        if alternatives:
            st.sidebar.caption("Alternatives", help="Other ideas you explored at this step.")
            for sib in alternatives:
                if st.sidebar.button(f"↪️ {truncate(sib['summary'], 25)}", key=f"nav_alt_{sib['id']}", help=f"Switch to: {sib['summary']}"):
                    navigate_to_node(tree, sib['id'])
                    if "editor_version" in st.session_state:
                        st.session_state.editor_version += 1
                    st.rerun()

    # 3. Direct Jump (Dropdown)
    st.sidebar.divider()
    st.sidebar.caption("🔍 Jump to any node", help="Directly jump to any specific idea in the tree.")
    
    # Sort nodes by creation order or hierarchy? Hierarchy is better but harder to sort flat list.
    # Let's just list them all with depth indentation.
    all_nodes_list = list(tree["nodes"].values())
    
    # Simple sort by ID (approx creation time) to keep order stable
    all_nodes_list.sort(key=lambda x: x["id"])
    
    def format_node_option(n):
        depth = get_depth(tree, n["id"])
        prefix = "— " * depth
        label = truncate(n["summary"], 40)
        return f"{prefix}{label}"
        
    # Find index of current
    current_idx = 0
    for idx, n in enumerate(all_nodes_list):
        if n["id"] == current_id:
            current_idx = idx
            break
 
    target_node = st.sidebar.selectbox(
        "Select Node", 
        all_nodes_list, 
        format_func=format_node_option,
        index=current_idx,
        key="jump_box",
        help="Choose a node from the full list."
    )
    
    if st.sidebar.button("Go", key="jump_btn", use_container_width=True, help="Navigate to the selected node."):
         if target_node["id"] != current_id:
            # Root Navigation = Reset Context
            if target_node["type"] == "root":
                st.session_state.pinned_context = []
                st.session_state.selected_paths = []
                st.session_state.banned_ideas = []
            
            navigate_to_node(tree, target_node['id'])
            if "editor_version" in st.session_state:
                st.session_state.editor_version += 1
            st.rerun()
