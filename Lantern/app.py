import streamlit as st
import base64
import os
# הערה: וודא שהקבצים controller.py, tree.py, definitions.py נמצאים באותה תיקייה
from definitions import UserEventType, ActionType
from tree import init_tree, get_current_node, get_children, navigate_to_node
from controller import handle_event

# 1. Page Configuration
st.set_page_config(page_title="Lantern", layout="wide")


# --- Image Handling Logic ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None


LOGO_FILENAME = 'logo.jpg'
logo_base64 = get_base64_of_bin_file(LOGO_FILENAME)

# CSS Styling
st.markdown(f"""
<style>
    /* Button Styling */
    .stButton button {{
        width: 100%;
        border-radius: 8px;
        height: 2.8em;
        font-weight: 500;
        border: 1px solid #e0e0e0;
        transition: all 0.2s;
    }}
    .stButton button:hover {{
        border-color: #0072b1;
        color: #0072b1;
    }}

    /* Delete Button Styling (Red) */
    .delete-btn button {{
        border-color: #ffcdd2;
        color: #c62828;
    }}
    .delete-btn button:hover {{
        background-color: #ffebee;
        border-color: #c62828;
    }}

    /* --- Sidebar Logo & Title Styling (VERTICAL LAYOUT) --- */
    .sidebar-header {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-bottom: 25px;
        /* תיקון: הוספת מרווח עליון כדי שהלוגו לא ייחתך */
        margin-top: 25px; 
        text-align: center;
    }}

    .sidebar-logo {{
        height: auto;
        width: auto;
        max-width: 120px;
        max-height: 120px;
        margin-bottom: 10px;
        object-fit: contain;
    }}

    .sidebar-title {{
        font-size: 3.5rem;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 800;
        margin: 0;
        line-height: 1.1;
        color: #0f172a;
        letter-spacing: -1px;
    }}

    /* Pinned Context Box */
    .pinned-box {{
        background-color: #fff9c4;
        padding: 10px;
        border-radius: 8px;
        border-left: 4px solid #fbc02d;
        margin-bottom: 10px;
        font-size: 0.9em;
    }}

    /* Status Pill Styling */
    .status-pill {{
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 25px;
    }}

    .status-container {{
        text-align: center;
        width: 100%;
    }}

    .status-explore {{ background-color: #e3f2fd; color: #1565c0; }}
    .status-critique {{ background-color: #ffebee; color: #c62828; }}
    .status-refine {{ background-color: #f3e5f5; color: #7b1fa2; }}
    .status-ready {{ background-color: #f5f5f5; color: #616161; border: 1px solid #e0e0e0; }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    .block-container {{
        padding-top: 2rem;
    }}
</style>
""", unsafe_allow_html=True)


def update_node_text():
    tree = st.session_state.tree
    current_id = tree["current"]
    widget_key = f"editor_{current_id}"
    new_text = st.session_state[widget_key]
    tree["nodes"][current_id]["summary"] = new_text


def get_ui_state(tree):
    if "last_critique" in st.session_state:
        return "Reviewing Argument", "status-critique"
    children = get_children(tree)
    if children:
        return "Exploring Ideas", "status-explore"
    return "Drafting Mode", "status-ready"


def main():
    # --- 1. Init State & Memory ---
    if "tree" not in st.session_state:
        st.session_state.tree = init_tree("")

    if "pinned_context" not in st.session_state:
        st.session_state.pinned_context = []

    if "banned_ideas" not in st.session_state:
        st.session_state.banned_ideas = []

    tree = st.session_state.tree
    current_node = get_current_node(tree)
    mode_label, mode_class = get_ui_state(tree)

    # 3. Layout
    col_editor, col_lantern = st.columns([2, 1], gap="large")

    # --- LEFT COLUMN: Editor ---
    with col_editor:
        st.subheader("What are we working on today?")

        editor_key = f"editor_{current_node['id']}"

        st.text_area(
            label="Main Editor",
            value=current_node["summary"],
            height=700,
            label_visibility="collapsed",
            placeholder="Paste your draft or start writing. Lantern is ready to assist.",
            key=editor_key,
            on_change=update_node_text
        )

    # --- RIGHT COLUMN: Lantern Sidebar ---
    with col_lantern:
        # --- LOGO & TITLE ---
        if logo_base64:
            st.markdown(f"""
                <div class="sidebar-header">
                    <img src="data:image/jpeg;base64,{logo_base64}" class="sidebar-logo" alt="Logo">
                    <div class="sidebar-title">Lantern</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="sidebar-header">
                    <div style="font-size: 5rem; line-height: 1;">🏮</div>
                    <div class="sidebar-title">Lantern</div>
                </div>
            """, unsafe_allow_html=True)

        # Status Pill
        st.markdown(f"""
            <div class="status-container">
                <div class="status-pill {mode_class}">
                    🟢 {mode_label}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- PINNED CONTEXT AREA ---
        if st.session_state.pinned_context:
            st.markdown("##### 📌 Pinned Ideas (Context)")
            for i, context_item in enumerate(st.session_state.pinned_context):
                st.markdown(f'<div class="pinned-box">{context_item}</div>', unsafe_allow_html=True)
            st.divider()

        # --- AGENT DECK ---
        st.write("**Agent Deck**")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔀 Idea Expander"):
                with st.spinner("Broadening perspectives..."):
                    # הכנת הקונטקסט לשליחה ל-Controller
                    context_data = {
                        "action": ActionType.DIVERGE,
                        "pinned_context": st.session_state.pinned_context,
                        "banned_ideas": st.session_state.banned_ideas
                    }
                    handle_event(tree, UserEventType.ACTION, context_data)

                    if "last_critique" in st.session_state: del st.session_state["last_critique"]
                    st.rerun()

        with col_btn2:
            if st.button("😈 Devil's Advocate"):
                with st.spinner("Analyzing logical gaps..."):
                    # הכנת הקונטקסט לשליחה ל-Controller
                    context_data = {
                        "action": ActionType.CRITIQUE,
                        # גם בביקורת חשוב לדעת מה ההקשר ומה נחסם
                        "pinned_context": st.session_state.pinned_context,
                        "banned_ideas": st.session_state.banned_ideas
                    }
                    response = handle_event(tree, UserEventType.ACTION, context_data)
                    st.session_state["last_critique"] = response.get("text")
                    st.rerun()

        if st.button("✨ Polisher (Refine)"):
            with st.spinner("Polishing style and tone..."):
                # הכנת הקונטקסט לשליחה ל-Controller
                context_data = {
                    "action": ActionType.REFINE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas
                }
                handle_event(tree, UserEventType.ACTION, context_data)

                if "last_critique" in st.session_state: del st.session_state["last_critique"]
                st.rerun()

        # Results Areas
        if "last_critique" in st.session_state:
            st.markdown("---")
            st.subheader("Critical Analysis")
            with st.chat_message("assistant", avatar="😈"):
                st.write(st.session_state["last_critique"])

            if st.button("Dismiss & Focus"):
                del st.session_state["last_critique"]
                st.rerun()

        children = get_children(tree)
        # סינון ילדים חסומים
        valid_children = [
            c for c in children
            if c['id'] not in st.session_state.banned_ideas
        ]

        if valid_children and "last_critique" not in st.session_state:
            st.markdown("---")
            st.subheader("Suggested Directions")

            for idx, child in enumerate(valid_children):
                with st.container(border=True):
                    # st.markdown(f"**Path {idx + 1}**") # אפשר להוריד את הכותרת אם רוצים עיצוב נקי יותר
                    st.write(child["summary"])

                    c1, c2 = st.columns(2)
                    # כפתור שמירה להקשר
                    with c1:
                        if st.button(f"📌 Keep as Context", key=f"pin_{child['id']}"):
                            st.session_state.pinned_context.append(child["summary"])
                            st.rerun()

                    # כפתור מחיקה/חסימה
                    with c2:
                        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                        if st.button(f"🚫 Dismiss", key=f"ban_{child['id']}"):
                            st.session_state.banned_ideas.append(child['id'])
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

        if current_node["parent"]:
            st.markdown("---")
            if st.button("↩️ Undo / Back to previous version"):
                navigate_to_node(tree, current_node["parent"])
                if "last_critique" in st.session_state: del st.session_state["last_critique"]
                st.rerun()


if __name__ == "__main__":
    main()