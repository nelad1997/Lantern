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
.stButton button { border-radius: 8px; font-weight: 500; transition: all 0.2s; }
.sidebar-header { display: flex; flex-direction: column; align-items: center; margin-bottom: 20px; }
.sidebar-logo { max-width: 110px; width: 110px; height: auto; opacity: 0.65; margin-bottom: 6px; filter: grayscale(20%); }
.pinned-box { background-color: #fefce8; padding: 12px; border-radius: 6px; border-left: 4px solid #eab308; margin-bottom: 8px; font-size: 0.85rem; color: #422006; }
.suggestion-card { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.suggestion-meta { display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase; }
.suggestion-text { font-size: 0.95rem; color: #334155; line-height: 1.5; margin-bottom: 12px; }
.status-pill { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
.status-explore { background-color: #e0f2fe; color: #0369a1; }
.status-reflect { background-color: #fef3c7; color: #92400e; }
.status-ready { background-color: #f0fdf4; color: #166534; }
.action-bar {
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px 16px 16px 16px;
    margin-bottom: 16px;
    background-color: #f9fafb;
}

.action-bar-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #475569;
    margin-bottom: 10px;
}

.stButton button {
    border-radius: 8px;
    font-weight: 500;
    margin-top: 4px;
}


</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def get_ui_state(tree):
    if "last_perspective" in st.session_state:
        return "Reflecting", "status-reflect"
    current_node = get_current_node(tree)
    has_valid_children = any(cid not in st.session_state.banned_ideas for cid in current_node["children"])
    if has_valid_children:
        return "Exploring", "status-explore"
    return "Drafting", "status-ready"


# -------------------------------------------------
# Main App
# -------------------------------------------------
def main():
    if "pending_action" not in st.session_state:
        st.session_state.pending_action = None

    if "is_thinking" not in st.session_state:
        st.session_state.is_thinking = False
    if "tree" not in st.session_state:
        st.session_state.tree = init_tree("")
    if "pinned_context" not in st.session_state:
        st.session_state.pinned_context = []
    if "banned_ideas" not in st.session_state:
        st.session_state.banned_ideas = []
    if "selected_paths" not in st.session_state:
        st.session_state.selected_paths = []


    tree = st.session_state.tree
    current_node = get_current_node(tree)
    mode_label, mode_class = get_ui_state(tree)

    col_editor, col_lantern = st.columns([2, 1], gap="large")

    # ==========================================
    # LEFT COLUMN: EDITOR
    # ==========================================
    with col_editor:
        st.subheader("Editor")

        st.markdown(
            """
            <div class="action-bar">
                <div class="action-bar-title">AI Reasoning Actions</div>
            """,
            unsafe_allow_html=True
        )

        st.session_state.setdefault("focused_text", current_node.get("summary", ""))

        c1, c2, c3 = st.columns([1, 1, 1], gap="small")

        with c1:
            if st.button("🌱 Expand", help="Explore new angles and expand thinking"):
                st.session_state.pending_action = {
                    "action": ActionType.DIVERGE,
                    "user_text": st.session_state["focused_text"],
                }
                st.session_state.is_thinking = True
                st.rerun()

        with c2:
            if st.button("⚖️ Critique", help="Challenge arguments and find weaknesses"):
                st.session_state.pending_action = {
                    "action": ActionType.CRITIQUE,
                    "user_text": st.session_state["focused_text"],
                }
                st.session_state.is_thinking = True
                st.rerun()

        with c3:
            if st.button("✨ Refine", help="Improve clarity and structure without changing ideas"):
                st.session_state.pending_action = {
                    "action": ActionType.REFINE,
                    "user_text": st.session_state["focused_text"],
                }
                st.session_state.is_thinking = True
                st.rerun()

        # ⬅️ סוגרים את ה-div
        st.markdown("</div>", unsafe_allow_html=True)

        # --- close AI Reasoning Actions wrapper ---
        st.markdown('</div>', unsafe_allow_html=True)

        # spacing + editor
        st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
        st.caption("✏️ Editing current reasoning node")

        html_content = st_quill(
            value=current_node.get("metadata", {}).get("html", ""),
            placeholder="Start writing...",
            html=True,
            toolbar=[
                ["bold", "italic", "underline"],
                [{"header": [1, 2, 3, False]}],
                [{"list": "ordered"}, {"list": "bullet"}],
            ],
            key=f"quill_{current_node['id']}",
        )

        blocks_data = []
        if html_content is not None:
            current_node.setdefault("metadata", {})["html"] = html_content
            plain_text = re.sub("<[^<]+?>", "", html_content).strip()
            current_node["summary"] = plain_text
            blocks = re.findall(r"<(p|h[1-6])[^>]*>(.*?)</\1>", html_content, re.DOTALL)
            for tag, inner_html in blocks:
                text = re.sub("<[^<]+?>", "", inner_html).strip()
                if text:
                    blocks_data.append({"text": text, "type": "header" if tag.startswith("h") else "paragraph"})

        focus_mode = st.selectbox("🧠 Focus Lantern on:", ["Whole document", "Specific block"])
        if focus_mode == "Specific block" and blocks_data:
            block_idx = st.number_input("Block number", min_value=1, max_value=len(blocks_data), step=1)
            st.session_state["focused_text"] = blocks_data[block_idx - 1]["text"]
        else:
            st.session_state["focused_text"] = current_node["summary"]

        with st.expander("🔍 AI Focus Preview", expanded=True):
            st.text_area("", value=st.session_state["focused_text"], height=100, disabled=True)

    # ==========================================
    # RIGHT COLUMN: LANTERN (SIDEBAR)
    # ==========================================
    with col_lantern:
        if logo_base64:
            st.markdown(
                f'<div class="sidebar-header"><img src="data:image/jpeg;base64,{logo_base64}" class="sidebar-logo"></div>',
                unsafe_allow_html=True)

        render_sidebar_map(tree)
        st.markdown("---")
        st.markdown(f'<div class="status-pill {mode_class}">State: {mode_label}</div>', unsafe_allow_html=True)

        # 📌 Pinned Context Section
        if st.session_state.pinned_context:
            st.markdown("<br><b>📌 Pinned Context</b>", unsafe_allow_html=True)
            for item in st.session_state.pinned_context:
                st.markdown(f'<div class="pinned-box">{item}</div>', unsafe_allow_html=True)
            if st.button("Clear Context"):
                st.session_state.pinned_context = []
                st.rerun()

        st.divider()

        # 💡 Critique Result (OUTSIDE Pinned Context Block)
        if "current_critiques" in st.session_state and st.session_state["current_critiques"]:
            st.subheader("💡 Critical Perspectives")
            if st.button("Dismiss All"):
                del st.session_state["current_critiques"]
                st.rerun()

            for i, item in enumerate(st.session_state["current_critiques"]):
                with st.container(border=True):
                    st.write(f"**#{i + 1}:** {item}")
                    c_pin, c_save, c_ign = st.columns([1, 1, 1])
                    with c_pin:
                        if st.button("📌 Pin", key=f"cp_{i}"):
                            st.session_state.pinned_context.append(f"Critique: {item}")
                            st.rerun()
                    with c_save:
                        if st.button("💾 Save", key=f"cs_{i}"):
                            handle_event(tree, UserEventType.ACTION,
                                         {"action": "SAVE_METADATA", "node_id": current_node["id"],
                                          "metadata_key": "critiques", "metadata_value": item})
                            st.session_state["current_critiques"].pop(i)
                            st.rerun()
                    with c_ign:
                        if st.button("✂️", key=f"ci_{i}"):
                            st.session_state["current_critiques"].pop(i)
                            st.rerun()
            st.divider()

        # ✨ Refined Changes (OUTSIDE Pinned Context Block)
        if "last_refine_diff" in st.session_state:
            st.subheader("✨ Refined Changes")
            st.markdown(
                f'<div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.9rem;">{st.session_state["last_refine_diff"]}</div>',
                unsafe_allow_html=True)
            if st.button("Dismiss Refinement"):
                del st.session_state["last_refine_diff"]
                st.rerun()
            st.divider()

        # 🌿 Suggested Paths
        def is_intro_like(text: str) -> bool:
            return (
                    "להלן" in text
                    and "הצעות" in text
                    and len(text) < 250
            )

        visible_children = []
        for cid in current_node["children"]:
            if cid in st.session_state.banned_ideas:
                continue

            text = tree["nodes"][cid]["summary"]
            if is_intro_like(text):
                continue  # ❌ לא מציגים כ-path

            visible_children.append(cid)

        if visible_children:
            st.subheader("Suggested Paths")

            st.caption(
                "Lantern generated alternative reasoning paths. "
                "Select one to continue, or discard those you do not wish to pursue."
            )

            for cid in visible_children:
                child = tree["nodes"][cid]

                with st.container():
                    st.markdown(
                        f'''
                        <div class="suggestion-card">
                            <div class="suggestion-meta">
                                <span>🤖 {child.get("type", "Idea")}</span>
                                <span>{child.get("created_at", "")}</span>
                            </div>
                            <div class="suggestion-text">{child["summary"]}</div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )

                    c_sel, c_pin, c_pru = st.columns([1, 1, 1])

                    # ✅ SELECT
                    with c_sel:
                        if st.button(
                                "✅ Select",
                                key=f"s_{cid}",
                                help="Commit this idea without changing your text"
                        ):
                            # 🧠 בחירה לוגית בלבד (לא שינוי node)
                            st.session_state.selected_paths.append(cid)

                            # 📌 Pin אוטומטי
                            st.session_state.pinned_context.append(child["summary"])

                            # ✅ הגדרת sibling_ids (האחים) כדי להסתיר את שאר ההצעות
                            parent_id = current_node["id"]
                            sibling_ids = tree["nodes"][parent_id]["children"]

                            # ✂️ הסתרת שאר ההצעות
                            for sib_id in sibling_ids:
                                if sib_id != cid and sib_id not in st.session_state.banned_ideas:
                                    st.session_state.banned_ideas.append(sib_id)

                            # ניקוי תוצרים אחרים
                            st.session_state.pop("current_critiques", None)
                            st.session_state.pop("last_refine_diff", None)

                            st.rerun()

                    # 📌 PIN
                    with c_pin:
                        if st.button("📌 Pin", key=f"p_{cid}", help="Keep this idea as context"):
                            st.session_state.pinned_context.append(child["summary"])
                            st.rerun()

                    # ✂️ PRUNE
                    with c_pru:
                        if st.button("✂️ Remove", key=f"pr_{cid}", help="Discard this idea"):
                            st.session_state.banned_ideas.append(cid)
                            st.rerun()#chan

if __name__ == "__main__":
    main()