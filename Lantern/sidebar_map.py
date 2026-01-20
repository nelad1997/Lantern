import streamlit as st


def render_sidebar_map(tree):
    """
    מרנדר את מפת החשיבה ומוסיף חיווי ויזואלי (💡) לצמתים עם ביקורות שמורות.
    """
    st.sidebar.markdown("### 🗺️ Reasoning Map")

    dot_code = """
    digraph G {
        rankdir=TB;
        node [shape=box, style="rounded,filled", fontname="Arial", fontsize=10, width=1.5];
        edge [color="#cbd5e1", penwidth=1.5];
    """

    for node_id, node in tree["nodes"].items():
        if node_id in st.session_state.get("banned_ideas", []):
            continue

        is_current = (node_id == tree["current"])
        fillcolor = "#f5f3ff" if is_current else "#ffffff"
        fontcolor = "#7c3aed" if is_current else "#475569"

        # --- תיקון: בדיקה האם קיימות ביקורות שמורות במטא-דאטה ---
        # אנחנו בודקים אם המפתח 'critiques' קיים והאם הוא רשימה שאינה ריקה
        node_metadata = node.get("metadata", {})
        saved_critiques = node_metadata.get("critiques", [])

        # אם מדובר במחרוזת בודדת (בגלל שמירה ראשונה) או רשימה
        has_critiques = len(saved_critiques) > 0
        critique_icon = " 💡" if has_critiques else ""

        # בניית התווית של הצומת (כולל האייקון אם צריך)
        icon_prefix = "🏠 " if node.get("type") == "root" else ""
        label = f"{icon_prefix}{node['summary'][:20]}...{critique_icon}"

        # טקסט הריחוף (Tooltip)
        tooltip_text = node_metadata.get("one_liner")
        if not tooltip_text:
            tooltip_text = node["summary"][:100].replace('"', "'") + "..."
        else:
            tooltip_text = tooltip_text.replace('"', "'")

        dot_code += f'  "{node_id}" [label="{label}", fillcolor="{fillcolor}", fontcolor="{fontcolor}", tooltip="{tooltip_text}"];\n'

        if node["parent"] and node["parent"] not in st.session_state.get("banned_ideas", []):
            dot_code += f'  "{node["parent"]}" -> "{node_id}";\n'

    dot_code += "}"
    st.sidebar.graphviz_chart(dot_code, use_container_width=True)