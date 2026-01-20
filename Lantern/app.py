import streamlit as st
import base64
import json
import re
from streamlit_quill import st_quill

# --- Imports ---
from definitions import UserEventType, ActionType
from tree import init_tree, get_current_node, navigate_to_node
from controller import handle_event
from sidebar_map import render_sidebar_map
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(page_title="Lantern", layout="wide", page_icon="🌿")


# -------------------------------------------------
# Persistence Helpers
# -------------------------------------------------
def save_project(tree):
    return json.dumps(tree, indent=2, ensure_ascii=False)


def load_project(json_str):
    try:
        data = json.loads(json_str)
        st.session_state.tree = data
        st.session_state.banned_ideas = []
        st.session_state.pinned_context = []
        return True
    except Exception as e:
        st.error(f"Failed to load project: {e}")
        return False


# -------------------------------------------------
# Assets & Styling
# -------------------------------------------------
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


LOGO_FILENAME = "logo.jpg"
logo_base64 = get_base64_of_bin_file(LOGO_FILENAME)

st.markdown("""
<style>
.stButton button { border-radius: 8px; font-weight: 500; transition: all 0.2s; }
.sidebar-logo { max-width: 110px; width: 110px; opacity: 0.65; filter: grayscale(20%); margin: auto; display: block; }
.pinned-box { background-color: #fefce8; padding: 12px; border-radius: 6px; border-left: 4px solid #eab308; margin-bottom: 8px; font-size: 0.85rem; color: #422006; }
.suggestion-card { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.status-pill { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; margin-bottom: 10px; }
.status-explore { background-color: #e0f2fe; color: #0369a1; }
.status-reflect { background-color: #fef3c7; color: #92400e; }
.status-ready { background-color: #f0fdf4; color: #166534; }
.action-bar { border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px; background-color: #f9fafb; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def get_ui_state(tree):
    if st.session_state.get("current_critiques"): return "Reflecting", "status-reflect"
    current_node = get_current_node(tree)
    if any(cid not in st.session_state.get("banned_ideas", []) for cid in current_node["children"]):
        return "Exploring", "status-explore"
    return "Drafting", "status-ready"


# -------------------------------------------------
# Main App Logic
# -------------------------------------------------
def main():
    if "tree" not in st.session_state: st.session_state.tree = init_tree("")
    if "pending_action" not in st.session_state: st.session_state.pending_action = None
    if "is_thinking" not in st.session_state: st.session_state.is_thinking = False
    if "pinned_context" not in st.session_state: st.session_state.pinned_context = []
    if "banned_ideas" not in st.session_state: st.session_state.banned_ideas = []

    tree = st.session_state.tree
    current_node = get_current_node(tree)
    mode_label, mode_class = get_ui_state(tree)

    col_editor, col_lantern = st.columns([2, 1], gap="large")

    # ==========================================
    # LEFT COLUMN: EDITOR
    # ==========================================
    with col_editor:
        st.subheader("Editor")

        st.markdown('<div class="action-bar"><b>AI Reasoning Actions</b>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🌱 Expand", use_container_width=True):
                st.session_state.pending_action = {"action": ActionType.DIVERGE,
                                                   "user_text": st.session_state.get("focused_text", "")}
                st.session_state.is_thinking = True;
                st.rerun()
        with c2:
            if st.button("⚖️ Critique", use_container_width=True):
                st.session_state.pending_action = {"action": ActionType.CRITIQUE,
                                                   "user_text": st.session_state.get("focused_text", "")}
                st.session_state.is_thinking = True;
                st.rerun()
        with c3:
            if st.button("✨ Refine", use_container_width=True):
                st.session_state.pending_action = {"action": ActionType.REFINE,
                                                   "user_text": st.session_state.get("focused_text", "")}
                st.session_state.is_thinking = True;
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.session_state["focused_text"] = current_node.get("metadata", {}).get("full_content", current_node["summary"])

        html_content = st_quill(
            value=current_node.get("metadata", {}).get("html", ""),
            placeholder="Focus your reasoning here...",
            key=f"q_{current_node['id']}"
        )

        if html_content is not None:
            current_node.setdefault("metadata", {})["html"] = html_content
            if current_node.get("type") == "root" and not current_node.get("metadata", {}).get("one_liner"):
                current_node["summary"] = re.sub("<[^<]+?>", "", html_content).strip()[:50]

    # ==========================================
    # RIGHT COLUMN: LANTERN (SIDEBAR)
    # ==========================================
    with col_lantern:
        if logo_base64:
            st.markdown(f'<img src="data:image/jpeg;base64,{logo_base64}" class="sidebar-logo">',
                        unsafe_allow_html=True)

        with st.sidebar:
            st.markdown("### 💾 Project Management")
            st.download_button("📥 Export Project (JSON)", data=save_project(tree), file_name="lantern_project.json",
                               mime="application/json")
            uploaded_file = st.file_uploader("📤 Load Project", type="json")
            if uploaded_file:
                if load_project(uploaded_file.getvalue().decode("utf-8")):
                    st.success("Loaded!");
                    st.rerun()
            st.divider()

        render_sidebar_map(tree)

        if current_node["parent"]:
            if st.button("⏪ Undo (Back to Parent)", use_container_width=True):
                navigate_to_node(tree, current_node["parent"])
                parent_node = tree["nodes"][current_node["parent"]]
                for cid in parent_node["children"]:
                    if cid in st.session_state.banned_ideas:
                        st.session_state.banned_ideas.remove(cid)
                st.rerun()

        st.markdown(f'<div class="status-pill {mode_class}">State: {mode_label}</div>', unsafe_allow_html=True)

        with st.expander("📄 View Full Node Detail", expanded=False):
            full_content = current_node.get("metadata", {}).get("full_content", current_node["summary"])
            st.info(full_content)

        # 📌 Pinned Context
        if st.session_state.pinned_context:
            st.markdown("<br><b>📌 Pinned Context</b>", unsafe_allow_html=True)
            for item in st.session_state.pinned_context:
                st.markdown(f'<div class="pinned-box">{item}</div>', unsafe_allow_html=True)
            if st.button("Clear Context"):
                st.session_state.pinned_context = []
                st.rerun()

        st.divider()

        # 💡 Critical Perspectives (The Updated Block)
        if st.session_state.get("current_critiques"):
            st.subheader("💡 Critical Perspectives")

            if st.button("Dismiss All"):
                del st.session_state["current_critiques"];
                st.rerun()

            for i, item in enumerate(st.session_state["current_critiques"]):
                with st.container(border=True):
                    st.write(item)
                    c_pin, c_ign, c_save = st.columns(3)
                    with c_pin:
                        if st.button("📌", key=f"cp_{i}", help="Pin to context"):
                            st.session_state.pinned_context.append(f"Critique: {item}");
                            st.rerun()
                    with c_ign:
                        if st.button("✂️", key=f"ci_{i}", help="Dismiss this critique"):
                            st.session_state["current_critiques"].pop(i);
                            st.rerun()
                    with c_save:
                        if st.button("💾", key=f"cs_{i}", help="Save to node"):
                            handle_event(tree, UserEventType.ACTION,
                                         {"action": "SAVE_METADATA", "node_id": current_node["id"],
                                          "metadata_key": "critiques", "metadata_value": item})
                            st.session_state["current_critiques"].pop(i);
                            st.rerun()

        # 🌿 Suggested Paths
        visible_children = [cid for cid in current_node["children"] if cid not in st.session_state.banned_ideas]
        if visible_children:
            st.subheader("🌿 Suggested Paths")
            for cid in visible_children:
                child = tree["nodes"][cid]
                with st.container():
                    st.markdown(
                        f'<div class="suggestion-card"><b>{child["summary"]}</b><br><small>{child.get("metadata", {}).get("one_liner", "")}</small></div>',
                        unsafe_allow_html=True)
                    col_s, col_p = st.columns(2)
                    with col_s:
                        if st.button("✅ Select", key=f"sel_{cid}"):
                            p_html = current_node.get("metadata", {}).get("html", "")
                            ai_txt = child.get("metadata", {}).get("full_content", child["summary"])
                            child.setdefault("metadata", {})["html"] = f"{p_html}<br><blockquote>{ai_txt}</blockquote>"
                            navigate_to_node(tree, cid)
                            for sid in current_node["children"]:
                                if sid != cid: st.session_state.banned_ideas.append(sid)
                            st.rerun()
                    with col_p:
                        if st.button("✂️", key=f"pru_{cid}"):
                            st.session_state.banned_ideas.append(cid);
                            st.rerun()

    # AI Execution Logic
    if st.session_state.pending_action and st.session_state.is_thinking:
        try:
            with st.spinner("Lantern is reflecting..."):
                res = handle_event(tree, UserEventType.ACTION, {
                    **st.session_state.pending_action,
                    "pinned_context": st.session_state.pinned_context,
                    "banned_ideas": st.session_state.banned_ideas
                })
                action = st.session_state.pending_action["action"]
                if action == ActionType.CRITIQUE:
                    st.session_state["current_critiques"] = res.get("items", [])
                elif action == ActionType.REFINE:
                    st.session_state["last_refine_diff"] = res.get("diff_html")
                st.session_state.pending_action = None
                st.session_state.is_thinking = False
                st.rerun()
        except Exception as e:
            st.error(f"Reasoning Error: {e}")
            st.session_state.is_thinking = False
            st.session_state.pending_action = None


if __name__ == "__main__":
    main()