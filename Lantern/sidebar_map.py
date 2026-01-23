import streamlit as st
import graphviz
import os
import json
from tree import get_node, navigate_to_node, get_node_short_label


def render_sidebar_map(tree):
    """
    Renders the vertical 'Thought Tree' in the sidebar.
    """
    # תיקון נתיב ל-Windows
    graphviz_path = r'C:\Program Files\Graphviz\bin'
    if os.path.exists(graphviz_path) and graphviz_path not in os.environ['PATH']:
        os.environ['PATH'] += os.pathsep + graphviz_path

    st.sidebar.subheader("🗺️ Thought Tree")

    # --- מנגנון Bulletproofed Persistent (מונה שלא מתאפס) ---
    # יוצרים סט בהיסטוריה אם לא קיים
    if "bulletproof_history" not in st.session_state:
        st.session_state.bulletproof_history = set()

    # עוברים על הפריטים הנעוצים כרגע ומוסיפים להיסטוריה
    if "pinned_items" in st.session_state.tree:
        for item in st.session_state.tree["pinned_items"]:
            if isinstance(item, dict) and item.get("type") == "critique":
                # משתמשים בטקסט כמזהה ייחודי כי לפעמים אין ID
                unique_key = item.get("text", "")[:50]  # מספיק לקחת את ההתחלה לזיהוי
                st.session_state.bulletproof_history.add(unique_key)

    # המונה מבוסס על ההיסטוריה המצטברת
    critiques_count = len(st.session_state.bulletproof_history)
    # --------------------------------------------------------

    # מטריקות נוספות
    total_nodes = len(tree["nodes"])
    paths_explored = max(0, total_nodes - 1)

    with st.sidebar.container(border=True):
        st.markdown("<small><b>🧠 Thinking Depth</b></small>", unsafe_allow_html=True)
        c_p, c_c = st.columns(2)
        c_p.caption(f"🌱 Paths: {paths_explored}")
        c_c.caption(f"⚖️ Bulletproofed: {critiques_count}")

    st.sidebar.markdown("<div style='margin-bottom:15px'></div>", unsafe_allow_html=True)

    # סינון צמתים
    visible_nodes = []
    for nid in tree["nodes"]:
        if nid in st.session_state.get("banned_ideas", []):
            continue
        node = tree["nodes"][nid]
        if node["summary"] == "Idea" and len(node.get("children", [])) == 0:
            continue
        visible_nodes.append(nid)

    current_id = tree["current"]

    # --- מנוע הניווט והנעיצה האוטומטית ---
    def handle_navigation():
        new_id = st.session_state["nav_selection_box"]
        current_id_in_callback = st.session_state.tree["current"]

        if new_id != current_id_in_callback:
            # 1. שמירת עורך
            if "editor_html" in st.session_state:
                st.session_state.tree["nodes"][current_id_in_callback].setdefault("metadata", {})["html"] = \
                    st.session_state["editor_html"]
                st.session_state.tree["nodes"][current_id_in_callback]["metadata"][
                    "draft_plain"] = st.session_state.get("focused_text", "")

            # 2. ניווט
            navigate_to_node(st.session_state.tree, new_id)

            # 3. טעינת עורך
            target_node = st.session_state.tree["nodes"][new_id]
            st.session_state["editor_html"] = target_node.get("metadata", {}).get("html", "")

            # 4. נעיצה אוטומטית (Auto-Pin Logic)
            if target_node["type"] != "root":
                meta = target_node.get("metadata", {})
                title = meta.get("label", get_node_short_label(target_node))
                full_text = meta.get("explanation", target_node.get("summary", ""))

                pin_obj = {
                    "id": new_id,
                    "title": title,
                    "text": full_text,
                    "type": "idea"
                }

                if not any(isinstance(item, dict) and item.get("id") == new_id for item in
                           st.session_state.tree["pinned_items"]):
                    st.session_state.tree["pinned_items"].append(pin_obj)

            # השמירה האוטומטית בוטלה כאן

    # מציאת האינדקס
    try:
        current_index = visible_nodes.index(current_id)
    except ValueError:
        current_index = 0

    st.sidebar.selectbox(
        "🎯 Select Node (Click to Pin & View):",
        options=visible_nodes,
        format_func=lambda nid: get_node_short_label(tree["nodes"][nid]),
        index=current_index,
        key="nav_selection_box",
        on_change=handle_navigation,
        help="Use this box to navigate. Selecting a node automatically PINS its full details."
    )

    # --- ויזואליזציה ---
    graph = graphviz.Digraph()
    graph.attr(rankdir='TB', nodesep='0.4', ranksep='0.6')
    graph.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', fontsize='16', margin='0.25',
               height='0.6')
    graph.attr('edge', color='#64748b', arrowsize='1.5', penwidth='1.5')

    for node_id in visible_nodes:
        node = tree["nodes"][node_id]
        is_current = (node_id == current_id)
        is_root = (node["type"] == "root")

        if is_root:
            fill, font, border, width = "#dcfce7", "#14532d", "#22c55e", "3"
        elif is_current:
            fill, font, border, width = "#7c3aed", "white", "#5b21b6", "4"
        else:
            fill, font, border, width = "#ffffff", "#0f172a", "#94a3b8", "1"

        label_text = node.get("metadata", {}).get("label", get_node_short_label(node))

        if label_text == "Idea": label_text = "New Path"

        import textwrap
        wrapped = "\n".join(textwrap.wrap(label_text, width=20))
        label = f"⚖️\n{wrapped}" if node.get("type") == "ai_critique" else wrapped

        tooltip = node.get("metadata", {}).get("explanation", node["summary"])[:200]

        graph.node(node_id, label=label, fillcolor=fill, fontcolor=font, color=border, penwidth=width,
                   tooltip=tooltip.replace('"', "'"))

        if node["parent"] and node["parent"] in visible_nodes:
            graph.edge(node["parent"], node_id)

    try:
        svg = graph.pipe(format='svg').decode('utf-8')
        st.sidebar.markdown(
            f'<div style="overflow-x: auto; overflow-y: auto; max-height: 600px; border: 1px solid #e2e8f0; border-radius: 8px; background: white;">{svg}</div>',
            unsafe_allow_html=True)
    except:
        st.sidebar.graphviz_chart(graph, use_container_width=True)

    # כפתור איפוס
    st.sidebar.divider()
    st.sidebar.caption("Reset Workspace")
    if st.sidebar.button("🗑️ Reset Full Tree", help="Delete all branches and context.", use_container_width=True):
        st.session_state.tree = {"nodes": {}, "current": ""}
        st.session_state.clear()
        # איפוס גם להיסטוריית הביקורות
        if "bulletproof_history" in st.session_state:
            del st.session_state["bulletproof_history"]

        if os.path.exists("lantern_autosave.json"):
            try:
                os.remove("lantern_autosave.json")
            except:
                pass
        st.rerun()