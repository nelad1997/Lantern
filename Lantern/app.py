import streamlit as st
import base64

# --- Imports ---
from definitions import UserEventType, ActionType
from tree import init_tree, get_current_node
from controller import handle_event
from sidebar_map import render_sidebar_map
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(page_title="Lantern", layout="wide")


# -------------------------------------------------
# Image / Assets
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
# Styling (CSS)
# -------------------------------------------------
st.markdown("""
<style>
/* Global Button Styling */
.stButton button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s;
}

/* Sidebar Header */
.sidebar-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 20px;
}
.sidebar-logo {
    max-width: 140px;
    opacity: 0.9;
}
.sidebar-title {
    font-size: 2rem;
    font-weight: 800;
    color: #1e293b;
}

/* Pinned Context Styling */
.pinned-box {
    background-color: #fefce8;
    padding: 12px;
    border-radius: 6px;
    border-left: 4px solid #eab308;
    margin-bottom: 8px;
    font-size: 0.85rem;
    color: #422006;
}

/* Suggestion Cards */
.suggestion-card {
    background-color: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.suggestion-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #94a3b8;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.suggestion-text {
    font-size: 0.95rem;
    color: #334155;
    line-height: 1.5;
    margin-bottom: 12px;
}

/* Status Pills */
.status-pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
}
.status-explore { background-color: #e0f2fe; color: #0369a1; }
.status-reflect { background-color: #fef3c7; color: #92400e; }
.status-ready { background-color: #f0fdf4; color: #166534; }

#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def update_node_text():
    """Update the current node's text from the editor."""
    tree = st.session_state.tree
    current_id = tree["current"]
    st.session_state.tree["nodes"][current_id]["summary"] = st.session_state[f"editor_{current_id}"]


def get_ui_state(tree):
    """Determine UI state/label based on tree status."""
    if "last_perspective" in st.session_state:
        return "Reflecting", "status-reflect"

    current_node = get_current_node(tree)
    # Check if there are un-banned children
    has_valid_children = any(cid not in st.session_state.banned_ideas for cid in current_node["children"])

    if has_valid_children:
        return "Exploring", "status-explore"
    return "Drafting", "status-ready"


# -------------------------------------------------
# Main App
# -------------------------------------------------
def main():
    # Initialize State
    if "tree" not in st.session_state:
        st.session_state.tree = init_tree("")
    if "pinned_context" not in st.session_state:
        st.session_state.pinned_context = []
    if "banned_ideas" not in st.session_state:
        st.session_state.banned_ideas = []

    tree = st.session_state.tree
    current_node = get_current_node(tree)
    mode_label, mode_class = get_ui_state(tree)

    # Layout Columns
    col_editor, col_lantern = st.columns([2, 1], gap="large")

    # ==========================================
    # LEFT COLUMN: EDITOR
    # ==========================================
    with col_editor:
        st.subheader("Editor")

        # --- Action Buttons ---
        c1, c2, c3 = st.columns([1, 1, 1], gap="small")

        with c1:
            if st.button("🌱 Expand"):
                handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.DIVERGE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas,
                    "user_text": current_node["summary"]
                })
                # מנקים את הביקורות הישנות אם עברנו פעולה
                st.session_state.pop("current_critiques", None)
                st.rerun()

        with c2:
            if st.button("⚖️ Critique"):
                response = handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.CRITIQUE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas,
                    "user_text": current_node["summary"]
                })

                # שומרים את הרשימה (items) במקום סתם טקסט
                st.session_state["current_critiques"] = response.get("items", [])
                st.rerun()

        with c3:
            if st.button("✨ Refine"):
                handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.REFINE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas,
                    "user_text": current_node["summary"]
                })
                st.session_state.pop("current_critiques", None)
                st.rerun()
        st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)

        # --- Main Text Editor ---
        editor_key = f"editor_{current_node['id']}"
        st.text_area(
            "Content",
            value=current_node["summary"],
            height=600,
            label_visibility="collapsed",
            key=editor_key,
            on_change=update_node_text,
            placeholder="Start typing your ideas here..."
        )

    # ==========================================
    # RIGHT COLUMN: LANTERN (SIDEBAR)
    # ==========================================
    with col_lantern:

        # --- 1. Logo & Header ---
        if logo_base64:
            st.markdown(f"""
            <div class="sidebar-header">
                <img src="data:image/jpeg;base64,{logo_base64}" class="sidebar-logo">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="sidebar-header"><div class="sidebar-title">Lantern</div></div>',
                        unsafe_allow_html=True)

        # --- 2. THE REASONING MAP ---
        render_sidebar_map(tree)

        st.markdown("---")

        # --- 3. Status & Pinned Context ---
        st.markdown(f'<div class="status-pill {mode_class}">State: {mode_label}</div>', unsafe_allow_html=True)

        # הצגת ההקשרים השמורים (Pinned)
        if st.session_state.pinned_context:
            st.markdown("<br><b>📌 Pinned Context</b>", unsafe_allow_html=True)
            for i, item in enumerate(st.session_state.pinned_context):
                st.markdown(f'<div class="pinned-box">{item}</div>', unsafe_allow_html=True)

            # תיקון: הסרנו את size="small"
            if st.button("Clear Context"):
                st.session_state.pinned_context = []
                st.rerun()
            st.divider()

        # --- 4. CRITIQUE / PERSPECTIVE RESULT ---
        if "current_critiques" in st.session_state and st.session_state["current_critiques"]:
            st.subheader("💡 Critical Perspectives")

            # כפתור לסגירת כל הביקורות בבת אחת
            if st.button("Dismiss All Critiques", key="dismiss_all_crit"):
                del st.session_state["current_critiques"]
                st.rerun()

            # לולאה שיוצרת כרטיס לכל הערה בנפרד
            for i, item in enumerate(st.session_state["current_critiques"]):

                with st.container(border=True):
                    # הצגת הטקסט של הביקורת
                    st.markdown(f"**Critique #{i + 1}**")
                    st.write(item)

                    c_pin, c_prune = st.columns([1, 1])

                    # --- כפתור PIN ---
                    with c_pin:
                        if st.button("📌 Pin & Fix", key=f"crit_pin_{i}",
                                     help="Add to context to fix in next draft"):
                            st.session_state.pinned_context.append(f"Fix: {item}")
                            st.session_state["current_critiques"].pop(i)
                            st.toast("Critique pinned to context!")
                            st.rerun()

                    # --- כפתור PRUNE ---
                    with c_prune:
                        if st.button("✂️ Ignore", key=f"crit_prune_{i}", help="Dismiss this critique"):
                            st.session_state["current_critiques"].pop(i)
                            st.rerun()

            # אם הרשימה התרוקנה
            if not st.session_state["current_critiques"]:
                del st.session_state["current_critiques"]
                st.rerun()

            st.divider()

        # --- 5. SUGGESTED PATHS (Children) ---
        all_child_ids = current_node["children"]
        visible_children = [cid for cid in all_child_ids if cid not in st.session_state.banned_ideas]

        if visible_children:
            st.subheader("Suggested Paths")

            for real_index, child_id in enumerate(all_child_ids):
                if child_id in st.session_state.banned_ideas:
                    continue

                child_node = tree["nodes"][child_id]
                created_at = child_node.get("created_at", "")
                node_type_icon = "🤖" if "ai" in child_node.get("type", "") else "📄"

                # כרטיס הצעה
                st.markdown(f"""
                <div class="suggestion-card">
                    <div class="suggestion-meta">
                        <span>{node_type_icon} {child_node.get('type', 'Idea')}</span>
                        <span>{created_at}</span>
                    </div>
                    <div class="suggestion-text">{child_node['summary']}</div>
                </div>
                """, unsafe_allow_html=True)

                # --- כפתורי הפעולה החדשים ---
                c_sel, c_pin, c_prune = st.columns([1.5, 1, 1])

                with c_sel:
                    # בחירה - הופך את זה לטקסט הראשי
                    if st.button("✅ Select", key=f"sel_{child_id}"):
                        handle_event(tree, UserEventType.CHOOSE_OPTION, {"option_index": real_index})
                        st.rerun()

                with c_pin:
                    # נעיצה - שומר כהקשר אבל לא עובר לשם
                    if st.button("📌 Pin", key=f"pin_{child_id}", help="Save as context"):
                        st.session_state.pinned_context.append(child_node["summary"])
                        st.toast("Idea Pinned to Context!", icon="📌")
                        st.rerun()

                with c_prune:
                    # גיזום/פסילה - מסתיר את הרעיון ומוסיף לרשימה שחורה
                    if st.button("✂️ Prune", key=f"prune_{child_id}", help="Discard and Ban"):
                        st.session_state.banned_ideas.append(child_id)
                        st.rerun()

if __name__ == "__main__":
    main()