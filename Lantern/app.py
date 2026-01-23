import streamlit as st
import base64
from streamlit_quill import st_quill
import re
import json
import os
import fitz  # PyMuPDF
from docx import Document
import io

# --- Imports ---
from definitions import UserEventType, ActionType
from tree import init_tree, get_current_node, navigate_to_node, get_node_short_label
from controller import handle_event, generate_diff_html, apply_fuzzy_replacement
from sidebar_map import render_sidebar_map
from dotenv import load_dotenv

load_dotenv(override=True)

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(page_title="Lantern", layout="wide")


# -------------------------------------------------
# File Processing Helpers
# -------------------------------------------------
def extract_text_from_file(uploaded_file):
    file_type = uploaded_file.name.split('.')[-1].lower()

    if file_type == 'pdf':
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    elif file_type == 'docx':
        doc = Document(io.BytesIO(uploaded_file.read()))
        return "\n".join([para.text for para in doc.paragraphs])

    elif file_type in ['txt', 'md']:
        return uploaded_file.getvalue().decode("utf-8")

    return None


# -------------------------------------------------
# Persistence Helpers
# -------------------------------------------------
AUTOSAVE_FILE = "lantern_autosave.json"


def save_autosave(tree):
    """
    DISABLED: This function intentionally does nothing.
    No file will be created on the disk.
    """
    pass


def load_autosave():
    """Tries to load the tree state from the local autosave file (if exists)."""
    if not os.path.exists(AUTOSAVE_FILE):
        return False
    try:
        with open(AUTOSAVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        st.session_state.tree = data
        if "pinned_items" not in st.session_state.tree:
            st.session_state.tree["pinned_items"] = []
        return True
    except Exception as e:
        return False


def save_project(tree):
    """Exports the project to a JSON string (in memory only)."""
    return json.dumps(tree, indent=2, ensure_ascii=False)


def load_project(json_str):
    try:
        data = json.loads(json_str)
        st.session_state.tree = data
        if "pinned_items" not in st.session_state.tree:
            st.session_state.tree["pinned_items"] = []
        st.session_state.banned_ideas = []
        # save_autosave is disabled
        return True
    except Exception as e:
        st.error(f"Failed to load project: {e}")
        return False


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
.sidebar-header { display: flex; flex-direction: column; align-items: center; margin-bottom: 5px; margin-top: -50px; }
.sidebar-logo { max-width: 80px; width: 80px; height: auto; opacity: 0.8; margin-bottom: 0px; filter: grayscale(10%); }
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
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def get_ui_state(tree):
    if "last_perspective" in st.session_state:
        return "Reflecting", "status-reflect"
    current_node = get_current_node(tree)
    type_map = {
        "root": ("Drafting", "status-ready"),
        "user": ("Drafting", "status-ready"),
        "ai_diverge": ("Exploring", "status-explore"),
        "ai_critique": ("Reflecting", "status-reflect"),
        "refine": ("Polishing", "status-ready"),
        "critique": ("Reflecting", "status-reflect")
    }
    node_type = current_node.get("type", "standard")
    if node_type in type_map:
        return type_map[node_type]
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
    if "root_topic_resolved" not in st.session_state:
        st.session_state.root_topic_resolved = False
    if "llm_in_flight" not in st.session_state:
        st.session_state.llm_in_flight = False
    if "tree" not in st.session_state:
        if not load_autosave():
            st.session_state.tree = init_tree("")
    if "pinned_items" not in st.session_state.tree:
        st.session_state.tree["pinned_items"] = []
    if "banned_ideas" not in st.session_state:
        st.session_state.banned_ideas = []
    if "selected_paths" not in st.session_state:
        st.session_state.selected_paths = []
    if "editor_version" not in st.session_state:
        st.session_state.editor_version = 0
    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = {}

    tree = st.session_state.tree
    current_node = get_current_node(tree)
    mode_label, mode_class = get_ui_state(tree)

    col_editor, col_lantern = st.columns([2, 1], gap="large")

    # ==========================================
    # LEFT COLUMN: EDITOR
    # ==========================================
    with col_editor:
        if "comparison_data" in st.session_state:
            st.subheader("⚖️ Branch Comparison")
            comp = st.session_state.comparison_data
            diff_html = generate_diff_html(comp['a']['summary'], comp['b']['summary'])
            st.markdown(
                f'<div style="background-color: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; line-height: 1.6;">{diff_html}</div>',
                unsafe_allow_html=True)
        else:
            st.subheader("Editor")

        st.markdown('<div class="action-bar"><div class="action-bar-title">AI Reasoning Actions</div>',
                    unsafe_allow_html=True)

        if "editor_html" not in st.session_state:
            st.session_state["editor_html"] = current_node.get("metadata", {}).get("html", "")
        st.session_state.setdefault("focused_text", current_node.get("summary", ""))

        c1, c2, c3 = st.columns([1, 1, 1], gap="small")
        with c1:
            if st.button("🌱 Expand", use_container_width=True):
                st.session_state.pending_action = {"action": ActionType.DIVERGE,
                                                   "user_text": st.session_state["focused_text"]}
                st.session_state.is_thinking = True
                st.rerun()
        with c2:
            if st.button("⚖️ Critique", use_container_width=True):
                st.session_state.pending_action = {"action": ActionType.CRITIQUE,
                                                   "user_text": st.session_state["focused_text"]}
                st.session_state.is_thinking = True
                st.rerun()
        with c3:
            if st.button("✨ Refine", use_container_width=True):
                st.session_state.pending_action = {"action": ActionType.REFINE,
                                                   "user_text": st.session_state["focused_text"]}
                st.session_state.is_thinking = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
        st.caption("✏️ Editing current reasoning node")

        if "html" not in current_node.get("metadata", {}) or not current_node["metadata"]["html"]:
            if current_node.get("summary"):
                current_node.setdefault("metadata", {})[
                    "html"] = f"<p>{current_node['summary'].replace(chr(10), '<br>')}</p>"

        if "last_refine_diff" in st.session_state:
            st.info("✨ AI Suggested Improvements (Review Mode)")
            st.markdown(
                f'<div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.9rem; line-height: 1.6; color: #334155; margin-bottom: 10px;">{st.session_state["last_refine_diff"]}</div>',
                unsafe_allow_html=True)
            c_acc, c_dis = st.columns([1, 1])
            with c_acc:
                if st.button("✅ Accept Changes", use_container_width=True, type="primary"):
                    new_text = st.session_state["last_refine_text"]
                    st.session_state["editor_html"] = new_text
                    current_node.setdefault("metadata", {})["html"] = new_text

                    # Force Editor Refresh
                    st.session_state.editor_version += 1

                    del st.session_state["last_refine_diff"], st.session_state["last_refine_text"]
                    st.rerun()
            with c_dis:
                if st.button("❌ Discard", use_container_width=True):
                    del st.session_state["last_refine_diff"], st.session_state["last_refine_text"];
                    st.rerun()
            html_content = st.session_state["editor_html"]
        else:
            html_content = st_quill(
                value=st.session_state["editor_html"],
                placeholder="Start drafting...",
                html=True,
                key=f"quill_main_{st.session_state.editor_version}",
            )

        plain_text = ""
        blocks_data = []  # Ensure initialization

        if html_content:
            st.session_state["editor_html"] = html_content
            current_node.setdefault("metadata", {})["html"] = html_content
            text_processing = re.sub(r"<(/?p|/?div|/h[1-6])>", "\n\n", html_content).replace("<br>", "\n")
            plain_text = re.sub("<[^<]+?>", "", text_processing).strip()
            current_node["metadata"]["draft_plain"] = plain_text

            if not st.session_state.get("root_topic_resolved", False) and current_node["type"] == "root":
                h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_content, re.IGNORECASE | re.DOTALL)
                if h1_match:
                    current_node["summary"] = re.sub("<[^<]+?>", "", h1_match.group(1)).strip()
                    st.session_state.root_topic_resolved = True;
                    st.rerun()

            blocks = re.findall(r"<(p|h[1-6])[^>]*>(.*?)</\1>", html_content, re.DOTALL)
            blocks_data = [{"text": re.sub("<[^<]+?>", "", inner).strip(),
                            "type": "header" if tag.startswith("h") else "paragraph"} for tag, inner in blocks if
                           inner.strip()]

        focus_mode = st.selectbox("🧠 Focus Lantern on:", ["Whole document", "Specific block"])
        if focus_mode == "Specific block" and blocks_data:
            block_idx = st.number_input("Block number", min_value=1, max_value=len(blocks_data), step=1)
            st.session_state["focused_text"] = blocks_data[block_idx - 1]["text"]
        else:
            st.session_state["focused_text"] = current_node.get("metadata", {}).get("draft_plain", plain_text)

        # ✅ PREVIEW BLOCK
        with st.expander("🔍 AI Focus Preview", expanded=False):
            st.caption("This is the exact text Lantern will analyze:")
            st.text_area("", value=st.session_state["focused_text"], height=100, disabled=True)

    # ==========================================
    # SIDEBAR TOOLS
    # ==========================================
    render_sidebar_map(tree)

    # ==========================================
    # RIGHT COLUMN: INTERACTION & CONTEXT
    # ==========================================
    with col_lantern:
        if logo_base64:
            st.markdown(
                f'<div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 5px;"><img src="data:image/jpeg;base64,{logo_base64}" style="width: 70px; opacity: 0.9;"></div>',
                unsafe_allow_html=True)
        st.markdown(
            f'<div class="status-pill {mode_class}" style="margin: 5px 0; width: 100%; text-align: center;">State: {mode_label}</div>',
            unsafe_allow_html=True)
        st.divider()

        with st.expander("📚 Knowledge Base", expanded=False):
            st.caption("Upload reference files (PDF, DOCX, TXT, MD) to provide more context.")
            uploaded_files = st.file_uploader("Upload reference files", type=["txt", "md", "pdf", "docx"],
                                              accept_multiple_files=True, key="kb_uploader")
            if uploaded_files:
                for f in uploaded_files:
                    if f.name not in st.session_state.knowledge_base:
                        extracted = extract_text_from_file(f)
                        if extracted: st.session_state.knowledge_base[f.name] = extracted
            if st.session_state.knowledge_base:
                for fname in list(st.session_state.knowledge_base.keys()):
                    c_f, c_d = st.columns([0.8, 0.2])
                    c_f.text(f"📄 {fname}")
                    if c_d.button("🗑️", key=f"del_{fname}"):
                        del st.session_state.knowledge_base[fname];
                        st.rerun()

        # 📌 Pinned Context Section (Scrollable)
        if st.session_state.tree["pinned_items"]:
            st.markdown("<br><b>📌 Pinned Context</b>", unsafe_allow_html=True)
            for i, item in enumerate(st.session_state.tree["pinned_items"]):
                is_node = isinstance(item, dict)
                p_text, p_title = (item.get("text", ""), item.get("title", "")) if is_node else (item, "")
                display_html = f"<strong>{p_title}</strong><br>{p_text}" if p_title else p_text
                c_txt, c_btns = st.columns([0.85, 0.15])
                with c_txt:
                    st.markdown(
                        f'<div class="pinned-box" style="max-height:150px; overflow-y:auto;">{display_html}</div>',
                        unsafe_allow_html=True)
                with c_btns:
                    if st.button("❌", key=f"unpin_{i}", use_container_width=True):
                        st.session_state.tree["pinned_items"].pop(i);
                        st.rerun()

        st.divider()

        # 💡 Critique logic (FIXED: Tooltip + Format)
        if "current_critiques" in st.session_state and st.session_state["current_critiques"]:
            st.subheader("💡 Critical Perspective")

            for i, item_data in enumerate(list(st.session_state["current_critiques"])):
                # Ensure we handle both dict (new format) and old string format for safety
                if isinstance(item_data, dict):
                    title = item_data.get("title", "Critique")
                    module = item_data.get("module", "Review")
                    text = item_data.get("text", "")
                else:
                    title = "Critique"
                    module = "Review"
                    text = item_data

                with st.container(border=True):
                    # Title with Tooltip (cursor: help)
                    st.markdown(
                        f'<div title="{module}" style="cursor: help; margin-bottom: 5px;">'
                        f'<b>{title}</b>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    # Body with scroll
                    st.markdown(
                        f"<div class='suggestion-text' style='max-height: 200px; overflow-y: auto;'>{text}</div>",
                        unsafe_allow_html=True)

                    # Only PIN and DEL buttons
                    c_pin, c_del = st.columns([1, 1])

                    with c_pin:
                        if st.button("📌 Pin", key=f"cs_pin_{i}", use_container_width=True):
                            st.session_state.tree["pinned_items"].append({
                                "id": None,  # Not a tree node
                                "title": title,
                                "text": text,
                                "type": "critique"
                            })
                            st.session_state["current_critiques"].pop(i)
                            st.rerun()

                    with c_del:
                        if st.button("🗑 Del", key=f"cs_del_{i}", use_container_width=True):
                            st.session_state["current_critiques"].pop(i)
                            st.rerun()

        # 🌿 Suggested Paths
        visible_children = []
        for cid in current_node["children"]:
            if cid not in st.session_state.banned_ideas and not any(
                    isinstance(p, dict) and p.get("id") == cid for p in st.session_state.tree["pinned_items"]):
                visible_children.append({"id": cid, "source": "Current"})

        if visible_children:
            st.subheader("Suggested Paths")
            st.caption("Lantern generated alternative reasoning paths. Select one to continue.")
            for item in visible_children:
                cid = item["id"]
                child = tree["nodes"][cid]
                meta = child.get("metadata", {})

                title = meta.get("label")
                explanation = meta.get("explanation")
                module_tag = meta.get("module", "Logic")

                raw_text = child["summary"]
                if not title or not explanation:
                    if "Title:" in raw_text:
                        parts = re.split(r"(Title:|Module:|Explanation:|Critique:)", raw_text)
                        try:
                            if "Title:" in parts:
                                title = parts[parts.index("Title:") + 1].strip().split('\n')[0].strip(" *")
                            if "Module:" in parts:
                                module_tag = parts[parts.index("Module:") + 1].strip().split('\n')[0]
                            if "Explanation:" in parts:
                                explanation = parts[parts.index("Explanation:") + 1].strip()
                            else:
                                explanation = raw_text
                        except:
                            title = "Alternative Path"
                            explanation = raw_text
                    else:
                        title = "Alternative Path"
                        explanation = raw_text

                if explanation:
                    explanation = re.sub(r'Title:.*?\n', '', explanation, flags=re.IGNORECASE)
                    explanation = re.sub(r'Module:.*?\n', '', explanation, flags=re.IGNORECASE)
                    explanation = explanation.replace("Title:", "").replace("Module:", "").replace("Explanation:",
                                                                                                   "").strip()

                with st.container(border=True):
                    st.markdown(
                        f'<div class="suggestion-meta"><span>🤖 {child.get("type", "Idea")}</span><span>From: {item["source"]}</span></div>',
                        unsafe_allow_html=True)
                    st.markdown(f"**{title}**")

                    st.markdown(
                        f'''
                        <div style="
                            max-height: 200px; 
                            overflow-y: auto; 
                            background-color: #f8fafc; 
                            padding: 8px; 
                            border-radius: 4px; 
                            border: 1px solid #e2e8f0;
                            font-size: 0.9em; 
                            color: #475569;">
                            {explanation}
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )

                    st.divider()
                    c_sel, c_pin, c_pru = st.columns([1, 1, 1])
                    with c_sel:
                        if st.button("✔ Select", key=f"s_{cid}", help=f"Academic Principle: {module_tag}",
                                     use_container_width=True):
                            pin_obj = {"id": cid, "title": title, "text": explanation, "type": "idea"}
                            st.session_state.tree["pinned_items"].append(pin_obj)

                            child.setdefault("metadata", {})["label"] = title
                            child.setdefault("metadata", {})["explanation"] = explanation
                            child.setdefault("metadata", {})["html"] = current_node.get("metadata", {}).get("html", "")

                            navigate_to_node(tree, cid);
                            st.rerun()
                    with c_pin:
                        if st.button("📌 Pin", key=f"p_{cid}", use_container_width=True):
                            st.session_state.tree["pinned_items"].append(
                                {"id": cid, "title": title, "text": explanation, "type": "idea"})
                            st.rerun()
                    with c_pru:
                        if st.button("🗑 Del", key=f"pr_{cid}", use_container_width=True):
                            st.session_state.banned_ideas.append(cid);
                            st.rerun()

        # Execute pending actions...
        if st.session_state.pending_action and st.session_state.is_thinking:
            if not st.session_state.llm_in_flight:
                st.session_state.llm_in_flight = True
                try:
                    payload = st.session_state.pending_action
                    response = handle_event(st.session_state.tree, UserEventType.ACTION, {
                        "action": payload["action"],
                        "pinned_context": st.session_state.tree["pinned_items"],
                        "banned_ideas": st.session_state.banned_ideas,
                        "user_text": payload["user_text"],
                        "knowledge_base": st.session_state.get("knowledge_base", {}),
                    })
                    if payload["action"] == ActionType.CRITIQUE:
                        st.session_state["current_critiques"] = response.get("items", [])
                    elif payload["action"] == ActionType.REFINE:
                        st.session_state["last_refine_diff"] = response.get("diff_html")
                        st.session_state["last_refine_text"] = response.get("refined_text")
                        st.session_state["last_refine_original_target"] = payload["user_text"]
                except Exception as e:
                    st.error(f"❌ Gemini Error: {e}")
                finally:
                    st.session_state.llm_in_flight = False
                    st.session_state.pending_action = None
                    st.session_state.is_thinking = False
                    st.rerun()


if __name__ == "__main__":
    main()