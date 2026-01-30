import streamlit as st
import graphviz
import os
import re
import streamlit.components.v1 as components
from tree import init_tree, navigate_to_node, get_node_short_label, get_nearest_html


def render_svg_in_sidebar(svg: str, height_px: int = 480):
    """
    Renders SVG inside a fixed-height iframe with internal scrollbars.
    Centers small trees and allows scrolling for large ones.
    """
    # Use doubled curly braces {{ }} for CSS and JS to avoid f-string SyntaxError
    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          html, body {{
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden; 
            background: white;
            font-family: sans-serif;
          }}
          .wrap {{
            height: 100%;
            width: 100%;
            overflow: auto;                 /* ✅ Multi-directional scroll */
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            box-sizing: border-box;
            background: white;
            display: flex;                  /* Flex for centering */
          }}
          .inner {{
            margin: auto;                  /* ✅ Centers content when small, allows scroll when big */
            padding: 20px;
            width: fit-content;
            height: fit-content;
          }}
          svg {{
            display: block;
            width: auto !important;
            height: auto !important;
            max-width: none !important;
            max-height: none !important;
          }}
        </style>
      </head>
      <body>
        <div class="wrap" id="scroll-container">
          <div class="inner">
            {svg}
          </div>
        </div>
        <script>
          const wrap = document.getElementById('scroll-container');
          
          // 1. Restore scroll position on load
          const savedPos = sessionStorage.getItem('lanternTreeScroll');
          if (savedPos) {{
            const pos = JSON.parse(savedPos);
            requestAnimationFrame(() => {{
                wrap.scrollTop = pos.t;
                wrap.scrollLeft = pos.l;
            }});
          }}
          
          // 2. Save scroll position whenever user scrolls
          wrap.addEventListener('scroll', () => {{
            sessionStorage.setItem('lanternTreeScroll', JSON.stringify({{
              t: wrap.scrollTop,
              l: wrap.scrollLeft
            }}));
          }});
        </script>
      </body>
    </html>
    """
    components.html(html, height=height_px, scrolling=False)


def render_sidebar_map(tree, show_header: bool = True):
    """
    Renders the vertical 'Thought Tree' in the sidebar.
    """
    graph = None

    with st.sidebar:
        # Resolve Graphviz path (Windows specific)
        graphviz_path = r"C:\Program Files (x86)\Graphviz\bin"
        if not os.path.exists(graphviz_path):
            graphviz_path = r"C:\Program Files\Graphviz\bin"
        
        if os.path.exists(graphviz_path) and graphviz_path not in os.environ.get("PATH", ""):
            os.environ["PATH"] = graphviz_path + os.pathsep + os.environ.get("PATH", "")

        if show_header:
            st.subheader("🗺️ Thought Tree")

        # --- Metrics & Controls ---
        if "bulletproof_history" not in st.session_state:
            st.session_state.bulletproof_history = set()

        critiques_count = len(st.session_state.bulletproof_history)
        total_nodes = len(tree["nodes"])
        paths_explored = max(0, total_nodes - 1)

        with st.container(border=True):
            tooltip_text = (
                "Track your reasoning process with Lantern.&#10;"
                "🌱 Paths: Explored alternative reasoning lines.&#10;"
                "🛡️ Strength: Counts every time you 'Acknowledge' a critique or select an idea."
            )
            st.markdown(
                f"<small><b>🧠 Thinking Depth</b></small> "
                f"<span title=\"{tooltip_text}\" style=\"cursor: help; color: #64748b; font-size: 0.8em;\">ℹ️</span>",
                unsafe_allow_html=True
            )
            c_p, c_c = st.columns(2)
            c_p.caption(f"🌱 Paths: {paths_explored}")
            c_c.markdown(f"<span style='font-size:0.8rem;'>🛡️ Strength: {critiques_count}</span>", unsafe_allow_html=True)

        st.session_state["show_full_tree"] = False

        current_id = tree["current"]

        # Filter nodes
        visible_nodes = []
        for nid in tree["nodes"]:
            if nid in st.session_state.get("banned_ideas", []): continue
            node = tree["nodes"][nid]
            # Ensure current node is always visible, otherwise selection resets to root
            if nid != current_id and node.get("summary") == "Idea" and len(node.get("children", [])) == 0: continue
            visible_nodes.append(nid)

        # --- Dynamic Active Path (Ancestors) ---
        active_path = set()
        ptr = current_id
        while ptr and ptr in tree["nodes"]:
            parent = tree["nodes"][ptr].get("parent")
            if parent:
                active_path.add(parent)
                ptr = parent
            else:
                break

        def handle_navigation():
            # GUARD: Do not navigate automatically if AI is thinking or list is refreshing
            if st.session_state.get("is_thinking"):
                return
                
            new_id = st.session_state.get("nav_selection_box")
            if not new_id:
                return

            # DEFENSIVE: Ensure the target node still exists in the potentially reset session state
            tree = st.session_state.get("tree")
            if not tree or new_id not in tree.get("nodes", {}):
                # Fallback: Reset UI selection to whatever the tree thinks is current
                if tree and "current" in tree:
                     st.session_state["nav_selection_box"] = tree["current"]
                return

            if new_id != tree["current"]:
                from app import add_debug_log
                
                # 1. Capture Current Draft before Leaving
                old_id = tree["current"]
                current_draft = st.session_state.get("editor_html", "")
                if current_draft:
                    # Sync to the node we ARE CURRENTLY ON before moving
                    tree["nodes"][old_id].setdefault("metadata", {})["html"] = current_draft
                    add_debug_log(f"🔄 NAV: Saved {len(current_draft)} chars to old node {old_id}")
                
                # 2. Perform Navigation
                add_debug_log(f"🔄 NAV: Switching from {old_id} to {new_id}")
                navigate_to_node(tree, new_id)
                
                # 3. Resolve Target Content (with robust fallback)
                target_html = get_nearest_html(tree, new_id)
                add_debug_log(f"🔄 NAV: Resolved target HTML (success={bool(target_html)})") 
                
                # If target has NO saved state (like a new idea), 
                # we keep the current draft if they are related, but get_nearest_html 
                # already handles walking up the tree. 
                st.session_state["editor_html"] = target_html or current_draft
                
                # 4. Force Quill Re-mount
                if "editor_version" not in st.session_state:
                    st.session_state.editor_version = 0
                st.session_state.editor_version += 1
                
                # Auto-pin
                target_node = tree["nodes"][new_id]
                if target_node.get("type") != "root":
                    meta = target_node.get("metadata", {})
                    pin_obj = {
                        "id": new_id, 
                        "title": meta.get("label", get_node_short_label(target_node)), 
                        "text": meta.get("explanation", target_node.get("summary", "")), 
                        "type": "idea",
                        "scope": meta.get("scope", "Whole Document"),
                        "source_context": meta.get("source_context", "")
                    }
                    if "pinned_items" in tree:
                        if not any(isinstance(i, dict) and i.get("id") == new_id for i in tree["pinned_items"]):
                             tree["pinned_items"].append(pin_obj)
                             add_debug_log(f"📌 NAV: Auto-pinned node {new_id}")

                add_debug_log(f"🔄 NAV: Complete. New node={new_id}")
                st.rerun()

        try:
            current_index = visible_nodes.index(current_id)
        except:
            current_index = 0


        # --- Pre-calculate Unique Labels for Deduplication ---
        node_id_to_label = {}
        label_counts = {}
        for nid in visible_nodes:
            node = tree["nodes"][nid]
            base_label = node.get("metadata", {}).get("label", get_node_short_label(node))
            if base_label == "Idea": base_label = "New Path"
            
            if base_label not in label_counts:
                label_counts[base_label] = 1
                node_id_to_label[nid] = base_label
            else:
                label_counts[base_label] += 1
                node_id_to_label[nid] = f"{base_label} ({label_counts[base_label]})"

        st.selectbox(
            "🎯 Navigate:", 
            options=visible_nodes, 
            format_func=lambda nid: node_id_to_label.get(nid, nid), 
            index=current_index, 
            key="nav_selection_box", 
            on_change=handle_navigation,
            help="Use this box to navigate between different versions and ideas. Selecting a node automatically PINS its full details."
        )

        # Build graph
        graph = graphviz.Digraph()
        graph.attr(rankdir="TB", nodesep="0.4", ranksep="0.6")
        graph.attr("node", shape="box", style="rounded,filled", fontname="Helvetica", fontsize="14", margin="0.25", height="0.6")
        graph.attr("edge", color="#64748b", arrowsize="1.2")

        for node_id in visible_nodes:
            node = tree["nodes"][node_id]
            is_current = (node_id == current_id)
            is_root = (node.get("type") == "root")
            is_in_path = (node_id in active_path)

            if is_current:
                fill, font, border, width = "#7c3aed", "white", "#5b21b6", "4"
            elif is_root:
                fill, font, border, width = "#dcfce7", "#14532d", "#22c55e", "3"
            elif is_in_path:
                fill, font, border, width = "#fff7ed", "#9a3412", "#f97316", "2"
            else:
                fill, font, border, width = "#ffffff", "#0f172a", "#94a3b8", "1"

            # Resolve Label with Scope
            node_meta = node.get("metadata", {})
            scope_raw = node_meta.get('scope', '')
            
            # Map scope to short code
            scope_code = ""
            if "Paragraph" in scope_raw:
                try:
                    # Robust extraction of the number whether it has # or not
                    p_num = re.search(r"(\d+)", scope_raw).group(1)
                    scope_code = f"[P{p_num}] "
                except:
                    scope_code = "[P] "
            elif "Whole" in scope_raw:
                scope_code = "[WD] "
            
            base_label_raw = node_id_to_label.get(node_id, get_node_short_label(node))
            
            # Deduplication: If base_label_raw already starts with a marker, strip it before prepending scope_code
            if scope_code.strip():
                 base_label_raw = re.sub(r"^\[P\s*\d+\]\s*", "", base_label_raw, flags=re.IGNORECASE).strip()

            display_label = f"{scope_code}{base_label_raw}"

            import textwrap
            wrapped = "\n".join(textwrap.wrap(display_label, width=18))
            label = f"⚖️\n{wrapped}" if node.get("type") == "ai_critique" else wrapped
            
            tooltip_str = f"Focus: {scope_raw}\n\n" + node_meta.get("explanation", node.get("summary", ""))[:450]
            
            graph.node(
                node_id, 
                label=label, 
                fillcolor=fill, 
                fontcolor=font, 
                color=border, 
                penwidth=width,
                tooltip=tooltip_str.replace('"', "'")
            )

            if node.get("parent") and node["parent"] in visible_nodes:
                graph.edge(node["parent"], node_id)

        # ✅ Render (Center-aligned)
        try:
            svg = graph.pipe(format="svg").decode("utf-8")
            render_svg_in_sidebar(svg, height_px=480)
        except Exception as e:
            st.error(f"Graphviz Error: {e}")

        # --- Reset Button (Moved back to the bottom) ---
        st.divider()
        workspace_info = (
            "Workspace Management:&#10;&#10;"
            "🗑 Reset Full Tree: This will permanently delete all AI-generated branches, perspectives, "
            "and logical critiques. Your current editor text and uploaded files will be preserved "
            "and transferred to a new, clean root node."
        )
        st.markdown(
            f'<div style="display: flex; align-items: center; gap: 5px; margin-bottom: 5px;">'
            f'<span style="font-size: 0.8rem; color: #64748b; font-weight: 500;">Workspace Management</span>'
            f'<span title="{workspace_info}" style="cursor: help; background-color: #38bdf8; color: white; border-radius: 4px; padding: 1px 8px; font-size: 0.7em; font-weight: bold;">i</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button("🗑", help="Reset Full Tree: Delete all branches and AI context (keeps your text).", use_container_width=True):
            # Tree Reset: Clear branches/context but KEEP text
            current_text = st.session_state.get("editor_html", "")
            
            st.session_state.tree = init_tree("") # Start with empty root
            # Sync existing text to the new root node
            tree_ptr = st.session_state.tree
            root_id = tree_ptr["current"]
            tree_ptr["nodes"][root_id].setdefault("metadata", {})["html"] = current_text
            
            # Wiping session state context (AI history)
            st.session_state.banned_ideas = []
            st.session_state.dismissed_suggestions = set()
            st.session_state.bulletproof_history = set()
            st.session_state.selected_paths = []
            st.session_state.current_critiques = []
            st.session_state.pending_refine_edits = []
            st.session_state.focused_text = ""
            
            # Reset UI/Meta state
            st.session_state.root_topic_resolved = False
            st.session_state.last_edit_time = 0
            st.session_state.editor_version = st.session_state.get("editor_version", 0) + 1
            
            st.toast("Thought tree has been reset. Your draft is preserved.", icon="🌳")
            st.rerun()

    # --- Main Expansion ---
    if st.session_state.get("show_full_tree") and graph:
        with st.expander("🗺️ Expanded Thought Tree", expanded=True):
             st.graphviz_chart(graph, use_container_width=True)

