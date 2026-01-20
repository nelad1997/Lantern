import streamlit as st
import base64
from streamlit_quill import st_quill
import re


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
    max-width: 110px;
    width: 110px;
    height: auto;
    opacity: 0.65;
    margin-bottom: 6px;
    filter: grayscale(20%);
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

/* ---------- Action Bar ---------- */
.action-bar {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 10px 12px 14px 12px;
    margin-bottom: 10px;
    background-color: #f9fafb;
}

.action-bar-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #475569;
    display: block;
    margin-bottom: 6px;
}


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

        # -------------------------------------------------
        # Action Bar
        # -------------------------------------------------
        st.markdown(
            """
            <div class="action-bar">
                <span class="action-bar-title">AI Reasoning Actions</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # -------------------------------------------------
        # Ensure focused_text always exists
        # -------------------------------------------------
        st.session_state.setdefault(
            "focused_text",
            current_node.get("summary", "")
        )

        # -------------------------------------------------
        # Action Buttons
        # -------------------------------------------------
        c1, c2, c3 = st.columns([1, 1, 1], gap="small")

        with c1:
            if st.button("🌱 Expand"):
                handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.DIVERGE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas,
                    "user_text": st.session_state["focused_text"],
                })
                st.session_state.pop("current_critiques", None)
                st.rerun()

        with c2:
            if st.button("⚖️ Critique"):
                response = handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.CRITIQUE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas,
                    "user_text": st.session_state["focused_text"],
                })
                st.session_state["current_critiques"] = response.get("items", [])
                st.rerun()

        with c3:
            if st.button("✨ Refine"):
                response = handle_event(tree, UserEventType.ACTION, {
                    "action": ActionType.REFINE,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas,
                    "user_text": st.session_state["focused_text"],
                })

                # אם חזר Refine Diff – שומרים אותו להצגה
                if response and response.get("mode") == "refine":
                    st.session_state["last_refine_diff"] = response.get("diff_html")

                # ניקוי מצבים שלא רלוונטיים
                st.session_state.pop("current_critiques", None)
                st.rerun()

        st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)

        # -------------------------------------------------
        # Main Text Editor
        # -------------------------------------------------
        st.caption("✏️ Editing current reasoning node")

        html_content = st_quill(
            value=current_node.get("metadata", {}).get("html", ""),
            placeholder="Start writing your ideas here...",
            html=True,
            toolbar=[
                ["bold", "italic", "underline"],
                [{"header": [1, 2, 3, False]}],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["link", "blockquote"],
            ],
            key=f"quill_{current_node['id']}",
        )

        # -------------------------------------------------
        # Extract blocks (headers vs paragraphs)
        # -------------------------------------------------
        blocks_data = []

        if html_content is not None:
            current_node.setdefault("metadata", {})["html"] = html_content

            plain_text = re.sub("<[^<]+?>", "", html_content)
            current_node["summary"] = plain_text.strip()

            blocks = re.findall(
                r"<(p|h[1-6])[^>]*>(.*?)</\1>",
                html_content,
                re.DOTALL
            )

            for tag, inner_html in blocks:
                text = re.sub("<[^<]+?>", "", inner_html).strip()
                if not text:
                    continue

                is_header = tag.startswith("h") or len(text.splitlines()) == 1

                blocks_data.append({
                    "text": text,
                    "type": "header" if is_header else "paragraph"
                })

        # -------------------------------------------------
        # Focus Selection (number-based, no radio)
        # -------------------------------------------------
        focus_mode = st.selectbox(
            "🧠 What should Lantern focus on?",
            ["Whole document", "Specific block"],
            key="focus_mode",
        )

        if focus_mode == "Specific block" and blocks_data:
            block_idx = st.number_input(
                "Block number",
                min_value=1,
                max_value=len(blocks_data),
                step=1,
            )

            selected_block = blocks_data[block_idx - 1]
            focused_text = selected_block["text"]

            st.caption(f"Type: {selected_block['type'].capitalize()}")
        else:
            focused_text = current_node["summary"]

        # -------------------------------------------------
        # Single source of truth
        # -------------------------------------------------
        st.session_state["focused_text"] = focused_text

        # -------------------------------------------------
        # AI Focus Preview
        # -------------------------------------------------
        with st.expander("🔍 AI Focus Preview", expanded=True):
            st.caption("This is exactly what will be sent to Lantern when you use the action buttons.")
            st.text_area(
                "",
                value=st.session_state["focused_text"],
                height=160,
                disabled=True,
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
                        if st.button("📌 Pin", key=f"crit_pin_{i}", help="Save as context"):
                            # שמירת מצב העורך לפני rerun
                            current_node.setdefault("metadata", {})["html"] = (
                                current_node.get("metadata", {}).get("html", "")
                            )

                            # שמירת הביקורת עצמה כהקשר
                            st.session_state.pinned_context.append(f"Critique: {item}")

                            st.toast("Critique pinned to context!", icon="📌")
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

        # --- Refine Diff (Track Changes) ---
        if "last_refine_diff" in st.session_state:
            st.subheader("✨ Refined Changes")

            st.markdown(
                f"""
                <div style="
                    background-color: #f8fafc;
                    padding: 15px;
                    border-radius: 8px;
                    border: 1px solid #e2e8f0;
                    line-height: 1.6;
                    font-size: 0.95rem;
                ">
                    {st.session_state["last_refine_diff"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("Dismiss Refinement"):
                del st.session_state["last_refine_diff"]
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
                    if st.button("📌 Pin", key=f"pin_{child_id}", help="Save as context"):
                        # שמירת מצב העורך לפני rerun
                        current_node.setdefault("metadata", {})["html"] = (
                            current_node.get("metadata", {}).get("html", "")
                        )

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