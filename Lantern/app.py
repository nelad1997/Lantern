import streamlit as st
from definitions import UserEventType, ActionType
from tree import init_tree, get_current_node, get_children, navigate_to_node
from controller import handle_event

# 1. Page Configuration
st.set_page_config(page_title="Lantern", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .stButton button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
    .agent-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #d1d5db;
    }
    .focus-box {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #0072b1;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


def update_node_text():
    """
    פונקציה שנקראת אוטומטית בכל פעם שהמשתמש משנה את הטקסט.
    היא שומרת את הטקסט החדש לתוך העץ.
    """
    tree = st.session_state.tree
    current_id = tree["current"]
    # המפתח של הטקסט-בוקס הוא דינמי לפי ה-ID של הצומת
    widget_key = f"editor_{current_id}"

    # שליפת הטקסט החדש מה-Session State
    new_text = st.session_state[widget_key]

    # עדכון העץ
    tree["nodes"][current_id]["summary"] = new_text


def main():
    st.markdown("### 🏮 Lantern: Intelligent Thinking Partner")

    # 2. Initialize State
    if "tree" not in st.session_state:
        initial_text = (
            "The integration of artificial intelligence (AI) into educational systems "
            "represents one of the most significant technological shifts in modern pedagogy."
        )
        st.session_state.tree = init_tree(initial_text)

    tree = st.session_state.tree
    current_node = get_current_node(tree)

    # 3. Layout
    col_editor, col_lantern = st.columns([2, 1], gap="medium")

    # --- LEFT COLUMN: Editor ---
    with col_editor:
        st.subheader("📄 Document Editor")
        st.caption("Write your text here. Lantern will help you on the right.")

        # בניית מפתח ייחודי לתיבה כדי שתתאפס רק כשמחליפים צומת
        editor_key = f"editor_{current_node['id']}"

        st.text_area(
            label="Document Content",
            value=current_node["summary"],
            height=600,
            label_visibility="collapsed",
            key=editor_key,  # המפתח הייחודי
            on_change=update_node_text  # קריאה לפונקציית השמירה
        )

    # --- RIGHT COLUMN: Lantern Sidebar ---
    with col_lantern:
        st.subheader("🧠 Lantern Agent Deck")

        # Focus Box
        st.markdown('<div class="focus-box">', unsafe_allow_html=True)
        st.markdown("**Current Focus:**")
        st.caption(f"Node ID: {current_node['id'][:6]}...")
        # מציגים את הטקסט מהצומת (שמתעדכן בזמן אמת בזכות הפונקציה למעלה)
        preview_text = current_node["summary"][:150] + "..." if len(current_node["summary"]) > 150 else current_node[
            "summary"]
        st.write(preview_text)
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # Action Buttons
        st.write("**Choose an Agent:**")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔀 Idea Expander"):
                with st.spinner("Expanding perspectives..."):
                    handle_event(tree, UserEventType.ACTION, {"action": ActionType.DIVERGE})
                    st.rerun()

        with col_btn2:
            if st.button("😈 Devil's Advocate"):
                with st.spinner("Analyzing weaknesses..."):
                    response = handle_event(tree, UserEventType.ACTION, {"action": ActionType.CRITIQUE})
                    st.session_state["last_critique"] = response.get("text")
                    st.rerun()

        if st.button("✨ Polisher (Refine)"):
            with st.spinner("Polishing text..."):
                handle_event(tree, UserEventType.ACTION, {"action": ActionType.REFINE})
                st.rerun()

        # Dynamic Results Area

        # A. Critique
        if "last_critique" in st.session_state and st.session_state["last_critique"]:
            st.warning("**Devil's Advocate says:**")
            st.write(st.session_state["last_critique"])
            if st.button("Dismiss Critique"):
                del st.session_state["last_critique"]
                st.rerun()

        # B. Children / Options
        children = get_children(tree)
        if children:
            st.divider()
            st.markdown(f"**Generated Paths ({len(children)}):**")

            for idx, child in enumerate(children):
                with st.container(border=True):
                    st.markdown(f"**Option {idx + 1}**")
                    st.info(child["summary"])

                    if st.button(f"📌 Pin this path", key=child["id"]):
                        handle_event(tree, UserEventType.CHOOSE_OPTION, {"option_index": idx})
                        if "last_critique" in st.session_state:
                            del st.session_state["last_critique"]
                        st.rerun()

        # C. Back Navigation
        if current_node["parent"]:
            st.divider()
            if st.button("⬅️ Back to previous thought"):
                navigate_to_node(tree, current_node["parent"])
                st.rerun()


if __name__ == "__main__":
    main()