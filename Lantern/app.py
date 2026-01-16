import streamlit as st
import base64
import os
import json


from definitions import UserEventType, ActionType
from tree import init_tree, get_current_node, get_children, navigate_to_node
from controller import handle_event

from dotenv import load_dotenv
load_dotenv()

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(page_title="Lantern", layout="wide")

# -------------------------------------------------
# Image Handling
# -------------------------------------------------
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

LOGO_FILENAME = "logo.jpg"
logo_base64 = get_base64_of_bin_file(LOGO_FILENAME)

# -------------------------------------------------
# Styling
# -------------------------------------------------
st.markdown("""
<style>

/* ---------- Global Buttons ---------- */
.stButton button {
    width: 100%;
    height: 44px;
    border-radius: 10px;
    font-weight: 500;
    border: 1px solid #e0e0e0;
    transition: all 0.2s;
}
.stButton button:hover {
    border-color: #2563eb;
    color: #2563eb;
}

/* ---------- Sidebar Header ---------- */
.sidebar-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 16px 0 12px 0;
.sidebar-logo {
    max-width: 160px;                 /* הקטנה משמעותית */
    margin-bottom: 1px;
    opacity: 0.8;                   /* ריכוך כללי */
filter: drop-shadow(0 0 1px rgba(0,0,0,0.15));
}
.sidebar-title {
    font-size: 2.6rem;
    font-weight: 800;
    color: #0f172a;
}

/* ---------- Status ---------- */
.status-pill {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 18px;
}
.status-explore { background-color: #e0f2fe; color: #075985; }
.status-reflect { background-color: #fef3c7; color: #92400e; }
.status-ready { background-color: #f5f5f5; color: #525252; }

/* ---------- Agent Deck ---------- */
.agent-deck {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;
}

/* ---------- Pinned Context ---------- */
.pinned-box {
    background-color: #fefce8;
    padding: 10px;
    border-radius: 8px;
    border-left: 4px solid #eab308;
    margin-bottom: 8px;
    font-size: 0.9em;
}

/* ---------- Suggestions ---------- */
.suggestion-card {
    height: 190px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.suggestion-actions {
    display: flex;
    gap: 8px;
}

.delete-btn button {
    border-color: #fecaca;
    color: #b91c1c;
}
.delete-btn button:hover {
    background-color: #fee2e2;
    border-color: #b91c1c;
}

#MainMenu, footer { visibility: hidden; }

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def update_node_text():
    tree = st.session_state.tree
    current_id = tree["current"]
    st.session_state.tree["nodes"][current_id]["summary"] = st.session_state[f"editor_{current_id}"]

def get_ui_state(tree):
    if "last_perspective" in st.session_state:
        return "Considering an Alternative Perspective", "status-reflect"
    if get_children(tree):
        return "Exploring Directions", "status-explore"
    return "Drafting Mode", "status-ready"

# -------------------------------------------------
# Main App
# -------------------------------------------------
def main():
    if "tree" not in st.session_state:
        st.session_state.tree = init_tree("")
    if "pinned_context" not in st.session_state:
        st.session_state.pinned_context = []
    if "banned_ideas" not in st.session_state:
        st.session_state.banned_ideas = []

    tree = st.session_state.tree
    current_node = get_current_node(tree)
    mode_label, mode_class = get_ui_state(tree)

    col_editor, col_lantern = st.columns([2, 1], gap="large")

    # -------- Editor --------
    with col_editor:
        st.subheader("What are we working on today?")
        # -------- Agent Actions (moved here) --------
        c1, c2, c3 = st.columns([1, 1, 1], gap="small")


        with c1:
            if st.button("🌱 Idea Expander"):
                handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.DIVERGE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas
                })
                st.session_state.pop("last_perspective", None)
                st.rerun()

        with c2:
            if st.button("🔍 Counter Perspective"):
                response = handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.CRITIQUE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas
                })
                st.session_state["last_perspective"] = response.get("text")
                st.rerun()

        with c3:
            if st.button("✨ Refine Draft"):
                handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.REFINE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas
                })
                st.session_state.pop("last_perspective", None)
                st.rerun()

        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        editor_key = f"editor_{current_node['id']}"
        st.text_area(
            "Main Editor",
            value=current_node["summary"],
            height=700,
            label_visibility="collapsed",
            key=editor_key,
            on_change=update_node_text
        )

    # -------- Lantern --------
    with col_lantern:
        if logo_base64:
            st.markdown(f"""
            <div class="sidebar-header">
                <img src="data:image/jpeg;base64,{logo_base64}" class="sidebar-logo">
                <div class="sidebar-title">Lantern</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align:center">
            <div class="status-pill {mode_class}">🟢 {mode_label}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.pinned_context:
            st.markdown("##### 📌 Pinned Context")
            for item in st.session_state.pinned_context:
                st.markdown(f'<div class="pinned-box">{item}</div>', unsafe_allow_html=True)
            st.divider()


        # -------- Perspective --------
        if "last_perspective" in st.session_state:
            st.markdown("---")
            st.subheader("Alternative Perspective")
            with st.chat_message("assistant", avatar="🔍"):
                st.write(st.session_state["last_perspective"])

            if st.button("Dismiss & Continue Writing"):
                del st.session_state["last_perspective"]
                st.rerun()

        # -------- Suggestions --------
        children = [c for c in get_children(tree) if c["id"] not in st.session_state.banned_ideas]

        if children and "last_perspective" not in st.session_state:
            st.markdown("---")
            st.subheader("Suggested Directions")

            for child in children:
                with st.container(border=True):
                    st.markdown('<div class="suggestion-card">', unsafe_allow_html=True)
                    st.write(child["summary"])

                    st.markdown('<div class="suggestion-actions">', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button("📌 Keep as Context", key=f"pin_{child['id']}"):
                            st.session_state.pinned_context.append(child["summary"])
                            st.rerun()

                    with c2:
                        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                        if st.button("🚫 Dismiss", key=f"ban_{child['id']}"):
                            st.session_state.banned_ideas.append(child["id"])
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('</div></div>', unsafe_allow_html=True)

        if current_node["parent"]:
            st.markdown("---")
            if st.button("↩️ Back to Previous Version"):
                navigate_to_node(tree, current_node["parent"])
                st.session_state.pop("last_perspective", None)
                st.rerun()

if __name__ == "__main__":
    main()
