import streamlit as st
import graphviz
from tree import get_node, navigate_to_node, get_node_short_label

def render_sidebar_map(tree):
    """
    Renders the vertical 'Thought Tree' in the sidebar.
    """
    st.sidebar.subheader("🗺️ Thought Tree")
    
    # --- Value Feedback: Thinking Metrics ---
    total_nodes = len(tree["nodes"])
    paths_explored = max(0, total_nodes - 1)
    critiques_count = sum(1 for n in tree["nodes"].values() if n.get("type") == "ai_critique")
    
    with st.sidebar.container(border=True):
        st.markdown("<small><b>🧠 Thinking Depth</b></small>", unsafe_allow_html=True)
        c_p, c_c = st.columns(2)
        c_p.caption(f"🌱 Paths: {paths_explored}")
        c_c.caption(f"⚖️ Bulletproofed: {critiques_count}")
    
    st.sidebar.markdown("<div style='margin-bottom:15px'></div>", unsafe_allow_html=True)
    
    # --- Interactive Navigation ---
    # Solution for "Interactive Selection without URLs/Reloads"
    
    # Helper to get visible nodes
    visible_nodes = [nid for nid in tree["nodes"] if nid not in st.session_state.get("banned_ideas", [])]
    
    current_id = tree["current"]
    banned_ids = st.session_state.get("banned_ideas", [])
    
    # Callback to handle state persistence + navigation
    def handle_navigation():
        new_id = st.session_state["nav_selection_box"]
        current_id_in_callback = st.session_state.tree["current"] # Use session state directly
        
        # Only switch if changed
        if new_id != current_id_in_callback:
            # 1. SAVE: Persist current editor to OLD node
            if "editor_html" in st.session_state:
                st.session_state.tree["nodes"][current_id_in_callback].setdefault("metadata", {})["html"] = st.session_state["editor_html"]
                st.session_state.tree["nodes"][current_id_in_callback]["metadata"]["draft_plain"] = st.session_state.get("focused_text", "")
            
            # 2. NAVIGATE: Update pointer
            navigate_to_node(st.session_state.tree, new_id)
            
            # 3. LOAD: Update editor to NEW node
            st.session_state["editor_html"] = st.session_state.tree["nodes"][new_id].get("metadata", {}).get("html", "")
            
            # 4. AUTO-PIN: Commit this idea to context (User Request "Commit Navigation")
            target_node = st.session_state.tree["nodes"][new_id]
            if target_node["type"] != "root":
                if "pinned_items" not in st.session_state.tree:
                    st.session_state.tree["pinned_items"] = []
                
                # Check for duplicates
                if not any(item.get("id") == new_id for item in st.session_state.tree["pinned_items"]):
                    # Extract RICH context for pinning (User Request: "Richest available explanation")
                    # Priority: 1. Idea Text (AI Suggestion) 2. User Draft 3. One-Liner 4. Title fallback
                    meta = target_node.get("metadata", {})
                    pin_text = meta.get("idea_text")
                    
                    if not pin_text:
                         pin_text = meta.get("draft_plain")
                    if not pin_text:
                         pin_text = meta.get("one_liner")
                    if not pin_text:
                         pin_text = get_node_short_label(target_node)
                         
                    # Use Structured Object
                    pin_obj = {
                        "id": new_id, 
                        "title": get_node_short_label(target_node),
                        "text": pin_text,
                        "type": "idea"
                    }
                    st.session_state.tree["pinned_items"].append(pin_obj)
            
            # (Rerun happens automatically after callback)

    # Find current index for default
    try:
        current_index = visible_nodes.index(current_id)
    except ValueError:
        current_index = 0

    st.sidebar.selectbox(
        "🎯 Select Active Node (Focus):",
        options=visible_nodes,
        format_func=lambda nid: get_node_short_label(tree["nodes"][nid]),
        index=current_index,
        key="nav_selection_box",
        on_change=handle_navigation,
        help="Use this to pivot your view and work on a different branch of the tree."
    )

    graph = graphviz.Digraph()
    graph.attr(rankdir='TB') 
    graph.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', fontsize='10', margin='0.1')
    graph.attr('edge', color='#64748b') 
    
    for node_id, node in tree["nodes"].items():
        if node_id in banned_ids:
            continue
            
        # High Contrast Coloring
        is_current = (node_id == current_id)
        is_root = (node["type"] == "root")
        
        if is_root:
            fill_color = "#dcfce7" 
            font_color = "#14532d" 
            border_color = "#22c55e" 
            penwidth = "2"
        elif is_current:
            fill_color = "#7c3aed" 
            font_color = "white"
            border_color = "#5b21b6" 
            penwidth = "3"
        else:
            fill_color = "#ffffff" 
            font_color = "#0f172a" 
            border_color = "#94a3b8" 
            penwidth = "1"
        
        # Check for saved critiques
        node_metadata = node.get("metadata", {})
        saved_critiques = node_metadata.get("critiques", [])
        has_critiques = len(saved_critiques) > 0
        critique_icon = " 💡" if has_critiques else ""
        
        # Label Construction
        label_text = get_node_short_label(node)
        label = f"{label_text}{critique_icon}"
        
        # Tooltip
        tooltip_text = node_metadata.get("one_liner")
        if not tooltip_text:
             tooltip_text = node["summary"][:100].replace('"', "'") + "..."
        else:
             tooltip_text = tooltip_text.replace('"', "'")
        
        graph.node(
            node_id, 
            label=label, 
            fillcolor=fill_color, 
            fontcolor=font_color, 
            color=border_color, 
            penwidth=penwidth, 
            tooltip=tooltip_text
            # NO URL - Purely Visual (Use 'Jump to Node' selectbox above)
        )
        
        if node["parent"] and node["parent"] not in banned_ids:
             graph.edge(node["parent"], node_id)

    st.sidebar.graphviz_chart(graph, use_container_width=True)

    # 4. Reset Tool
    st.sidebar.divider()
    st.sidebar.caption("Reset Workspace", help="Completely wipe the tree and context to start a new session.")
    if st.sidebar.button("🗑️ Reset Full Tree", help="Permanently delete all branches and start a new session from scratch.", use_container_width=True):
        # 1. Clear State
        st.session_state.tree = {"nodes": {}, "current": ""} 
        st.session_state.clear()
        st.query_params.clear() # Fix: Ensure URL is cleared to prevent stuck navigation
        
        # 2. Delete Autosave File to prevent resurrection
        import os
        if os.path.exists("lantern_autosave.json"):
            try:
                os.remove("lantern_autosave.json")
            except:
                pass
        
        st.rerun()
