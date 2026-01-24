import streamlit as st
import base64
from streamlit_quill import st_quill
import re
import json
import os
import fitz  # PyMuPDF
from docx import Document
import io
import html  # Added for safe text escaping

# --- Imports ---
from definitions import UserEventType, ActionType
from tree import init_tree, get_current_node, navigate_to_node, get_node_short_label
from controller import handle_event, generate_diff_html, apply_fuzzy_replacement
from sidebar_map import render_sidebar_map
from dotenv import load_dotenv

# --- ReportLab Import Handling (Safe Import) ---
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

load_dotenv(override=True)

# -------------------------------------------------
# Page Configuration
# -------------------------------------------------
st.set_page_config(page_title="Lantern", layout="wide")


# -------------------------------------------------
# File Processing Helpers
# -------------------------------------------------
def extract_text_from_file(uploaded_file):
    # Reset file pointer to beginning (Crucial for Streamlit)
    uploaded_file.seek(0)

    file_type = uploaded_file.name.split('.')[-1].lower()

    try:
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

    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

    return None


# -------------------------------------------------
# Export Helpers
# -------------------------------------------------
def create_docx(text):
    doc = Document()
    for paragraph in text.split('\n'):
        if paragraph.strip():
            doc.add_paragraph(paragraph)

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


def create_pdf(text):
    if not HAS_REPORTLAB:
        return None

    bio = io.BytesIO()
    c = canvas.Canvas(bio, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica", 12)

    y = height - 50
    margin = 50

    for line in text.split('\n'):
        wrapped_lines = simpleSplit(line, "Helvetica", 12, width - 2 * margin)
        for wrapped_line in wrapped_lines:
            if y < 50:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = height - 50
            c.drawString(margin, y, wrapped_line)
            y -= 15
        y -= 5

    c.save()
    return bio.getvalue()


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
.status-pill { display: inline-block; padding: 10px 24px; border-radius: 35px; font-size: 1.1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06); width: 100%; text-align: center; }
.status-explore { background-color: #e0f2fe; color: #0369a1; border: 2px solid #bae6fd; }
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
/* Enhanced Typography */
.ql-editor {
    font-size: 18px !important;
    line-height: 1.6 !important;
}
.ql-container {
    font-size: 18px !important;
}
/* Consistent Scrollable Content for all panels */
.scrollable-content {
    max-height: 250px;
    overflow-y: auto;
    background-color: #f8fafc;
    padding: 8px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
    font-size: 0.9em;
    color: #475569;
}
/* Scrollbar styling */
.scrollable-content::-webkit-scrollbar {
    width: 6px;
}
.scrollable-content::-webkit-scrollbar-thumb {
    background-color: #cbd5e1;
    border-radius: 3px;
}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def get_ui_state(tree):
    if st.session_state.get("is_thinking", False):
         if st.session_state.pending_action:
             act = st.session_state.pending_action.get("action")
             if act == ActionType.DIVERGE: return "Expanding...", "status-explore"
             if act == ActionType.CRITIQUE: return "Critiquing...", "status-reflect"
             if act == ActionType.REFINE: return "Refining...", "status-ready"
         return "Thinking...", "status-explore"

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
        # Header (Cleaned up, removed Import/Export from here)
        if "comparison_data" in st.session_state:
            st.subheader("⚖️ Branch Comparison")
        else:
            st.subheader("Editor")

        if "comparison_data" in st.session_state:
            comp = st.session_state.comparison_data
            diff_html = generate_diff_html(comp['a']['summary'], comp['b']['summary'])
            st.markdown(
                f'<div style="background-color: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; line-height: 1.6;">{diff_html}</div>',
                unsafe_allow_html=True)

        st.markdown('<div class="action-bar"><div class="action-bar-title">AI Reasoning Actions</div>',
                    unsafe_allow_html=True)

        if "editor_html" not in st.session_state:
            st.session_state["editor_html"] = current_node.get("metadata", {}).get("html", "")
        st.session_state.setdefault("focused_text", current_node.get("summary", ""))

        c1, c2, c3 = st.columns([1, 1, 1], gap="small")
        with c1:
            if st.button("🌱 Expand", use_container_width=True, help="Generate new perspectives and ideas based on your text"):
                st.session_state.pending_action = {"action": ActionType.DIVERGE,
                                                   "user_text": st.session_state["focused_text"]}
                st.session_state.is_thinking = True
                st.rerun()
        with c2:
            if st.button("⚖️ Critique", use_container_width=True, help="Get critical feedback on logic, evidence, and rigor"):
                st.session_state.pending_action = {"action": ActionType.CRITIQUE,
                                                   "user_text": st.session_state["focused_text"]}
                st.session_state.is_thinking = True
                st.rerun()
        with c3:
            if st.button("✨ Refine", use_container_width=True, help="Polish grammar, clarity, and flow"):
                # Capture Context
                context = {
                    "mode": st.session_state.get("promo_focus_mode", "Whole document"),
                    "block_idx": st.session_state.get("promo_block_selector", 1)
                }
                
                st.session_state.pending_action = {"action": ActionType.REFINE,
                                                   "user_text": st.session_state["focused_text"],
                                                   "context": context}
                st.session_state.is_thinking = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)

        if "html" not in current_node.get("metadata", {}) or not current_node["metadata"]["html"]:
            if current_node.get("summary"):
                current_node.setdefault("metadata", {})[
                    "html"] = f"<p>{current_node['summary'].replace(chr(10), '<br>')}</p>"

        # Custom CSS to force editor font size inside the iframe (Defined here to be available globally)
        EDITOR_CSS = "<style>.ql-editor { font-size: 18px !important; line-height: 1.6; }</style>"

        if "last_refine_diff" in st.session_state:
            st.info("✨ AI Suggested Improvements (Review Mode)")
            st.markdown(
                f'<div class="scrollable-content" style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.9rem; line-height: 1.6; color: #334155; margin-bottom: 10px;">{st.session_state["last_refine_diff"]}</div>',
                unsafe_allow_html=True)
            c_acc, c_dis = st.columns([1, 1])
            with c_acc:
                if st.button("✅ Accept Changes", use_container_width=True, type="primary"):
                    new_text = st.session_state["last_refine_text"]
                    
                    # Context Parsing
                    ctx = st.session_state.get("last_refine_context", {})
                    mode = ctx.get("mode", "Whole document")
                    
                    if mode == "Specific paragraph":
                        # Smart Splicing Logic
                        # 1. Get full HTML
                        full_html = st.session_state["editor_html"]
                        # 2. Find all blocks again
                        blocks = list(re.finditer(r"<(p|h[1-6])[^>]*>(.*?)</\1>", full_html, re.DOTALL | re.IGNORECASE))
                        
                        target_idx = ctx.get("block_idx", 1) - 1 # 1-based to 0-based
                        
                        # Filter blocks same way as UI (ignore headers if heuristic applies, etc) - SIMPLIFIED FOR ROBUSTNESS
                        # To match exactly what user selected, we need to rebuild the filtered list index
                        # But here we simply assume the filtered list in UI maps 1:1 if we apply same filter
                        
                        # Re-filtering to find the correct match in the raw list
                        filtered_indices = []
                        for i, m in enumerate(blocks):
                            tag = m.group(1)
                            inner = m.group(2)
                            clean_inner = re.sub("<[^<]+?>", "", inner).replace("&nbsp;", " ").strip()
                            if clean_inner:
                                block_type = "header" if tag.lower().startswith("h") else "paragraph"
                                if block_type == "paragraph" and len(clean_inner) < 100:
                                     if re.search(r"<(strong|b)[^>]*>.*?</(strong|b)>", inner, re.DOTALL | re.IGNORECASE):
                                         inner_no_tags = re.sub("<[^<]+?>", "", inner).strip()
                                         if len(inner_no_tags) <= len(clean_inner) + 5:
                                             block_type = "header"
                                if block_type == "paragraph":
                                    filtered_indices.append(i)
                        
                        if 0 <= target_idx < len(filtered_indices):
                            real_match_idx = filtered_indices[target_idx]
                            match = blocks[real_match_idx]
                            start, end = match.span()
                            
                            # Construct replacement (wrap in <p> if plain text, or try to keep tag?)
                            # The refined text usually comes back as plain text or wrapped.
                            # We'll assume the LLM might strip tags, so we wrap in <p> if it looks like raw text.
                            replacement_block = new_text
                            if not replacement_block.strip().startswith("<"):
                                replacement_block = f"<p>{replacement_block}</p>"
                            
                            # Replace in full string
                            final_html = full_html[:start] + replacement_block + full_html[end:]
                            st.session_state["editor_html"] = final_html
                            current_node.setdefault("metadata", {})["html"] = final_html
                        else:
                             # Fallback if index mismatch
                             st.warning("Could not locate original paragraph to replace. Appending to end.")
                             st.session_state["editor_html"] += f"<br>{new_text}"
                             current_node.setdefault("metadata", {})["html"] = st.session_state["editor_html"]

                    else:
                        # Replace Whole Document
                        st.session_state["editor_html"] = new_text
                        current_node.setdefault("metadata", {})["html"] = new_text

                    # Force Editor Refresh
                    st.session_state.editor_version += 1

                    del st.session_state["last_refine_diff"], st.session_state["last_refine_text"]
                    if "last_refine_context" in st.session_state: del st.session_state["last_refine_context"]
                    st.rerun()
            with c_dis:
                if st.button("❌ Discard", use_container_width=True):
                    del st.session_state["last_refine_diff"], st.session_state["last_refine_text"];
                    st.rerun()
            html_content = st.session_state["editor_html"]
        else:
            
            # Prepend CSS to the value so it renders inside the iframe
            quill_value = EDITOR_CSS + st.session_state["editor_html"]
            
            html_content = st_quill(
                value=quill_value,
                placeholder="Start drafting...",
                html=True,
                key=f"quill_main_{st.session_state.editor_version}",
            )

        plain_text = ""
        blocks_data = []  # Ensure initialization

        if html_content:
            # Strip the injected CSS from the output to keep data clean
            clean_html = html_content.replace(EDITOR_CSS, "")
            
            st.session_state["editor_html"] = clean_html
            current_node.setdefault("metadata", {})["html"] = clean_html
            
            # Robust Text Processing (Fixes double counting of paragraphs)
            # 1. Replace block tags with SINGLE newline first (to avoid gaps)
            text_processing = re.sub(r"</(p|div|h[1-6])>", "\n", clean_html) 
            text_processing = re.sub(r"<(p|div|h[1-6])[^>]*>", "", text_processing)
            # 2. Convert <br> to newline
            text_processing = text_processing.replace("<br>", "\n")
            # 3. Strip tags
            plain_text = re.sub("<[^<]+?>", "", text_processing).strip()
            # 4. Collapse multiple newlines to max 2
            plain_text = re.sub(r'\n{3,}', '\n\n', plain_text)
            
            current_node["metadata"]["draft_plain"] = plain_text

            if not st.session_state.get("root_topic_resolved", False) and current_node["type"] == "root":
                h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_content, re.IGNORECASE | re.DOTALL)
                if h1_match:
                    current_node["summary"] = re.sub("<[^<]+?>", "", h1_match.group(1)).strip()
                    st.session_state.root_topic_resolved = True;
                    st.rerun()

            blocks = re.findall(r"<(p|h[1-6])[^>]*>(.*?)</\1>", html_content, re.DOTALL | re.IGNORECASE)
            blocks_data = []
            for tag, inner in blocks:
                # Clean inner text to check for emptiness (handle &nbsp;)
                clean_inner = re.sub("<[^<]+?>", "", inner).replace("&nbsp;", " ").strip()
                if clean_inner:
                    block_type = "header" if tag.lower().startswith("h") else "paragraph"
                    
                    # Heuristic: If it's a short bold paragraph, likely a title
                    if block_type == "paragraph" and len(clean_inner) < 100:
                         if re.search(r"<(strong|b)[^>]*>.*?</(strong|b)>", inner, re.DOTALL | re.IGNORECASE):
                             # Check if the bold covers most of the content
                             inner_no_tags = re.sub("<[^<]+?>", "", inner).strip()
                             if len(inner_no_tags) <= len(clean_inner) + 5: # Tolerance
                                 block_type = "header"

                    blocks_data.append({
                        "text": clean_inner,
                        "type": block_type
                    })

        focus_mode = st.selectbox("🧠 Focus Lantern on:", ["Whole document", "Specific paragraph"], key="promo_focus_mode")
        if focus_mode == "Specific paragraph" and blocks_data:
            # Filter only paragraphs for the "Paragraph number" selector
            paragraphs_only = [b for b in blocks_data if b["type"] == "paragraph"]
            
            if paragraphs_only:
                # Use "Paragraph number" as requested
                block_idx = st.number_input("Paragraph number", min_value=1, max_value=len(paragraphs_only), step=1, key="promo_block_selector")
                st.session_state["focused_text"] = paragraphs_only[block_idx - 1]["text"]
            else:
                st.warning("No paragraphs found.")
                st.session_state["focused_text"] = ""
        else:
            st.session_state["focused_text"] = current_node.get("metadata", {}).get("draft_plain", plain_text)

        # ✅ PREVIEW BLOCK (Hidden when in Refine Review Mode OR Thinking about Refine)
        is_refining = st.session_state.get("pending_action", {}) and \
                      st.session_state.pending_action.get("action") == ActionType.REFINE and \
                      st.session_state.is_thinking

        if "last_refine_diff" not in st.session_state and not is_refining:
            with st.expander("🔍 AI Focus Preview", expanded=False):
                st.caption("This is the exact text Lantern will analyze:")
                st.text_area("", value=st.session_state["focused_text"], height=150, disabled=True)


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

        # --- NEW: Tooltip & System Explanation ---
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 15px;">
                <span title="Welcome to Lantern 💡&#10;What is Lantern?&#10;An intelligent environment for academic writing and reasoning. It combines a text editor with an AI assistant to facilitate in-depth research and thought management.&#10;How to use it?&#10;&#10;✍️ Write: Draft your initial ideas in the main text editor.&#10;🧠 Collaborate with AI:&#10;🌱 Expand: Explore new lines of reasoning and deepen your discussion.&#10;⚖️ Critique: Receive constructive feedback grounded in academic principles.&#10;✨ Refine: Polish your phrasing, precision, and style.&#10;🗺️ Navigate: Use the Thought Tree (sidebar) to manage various drafts and focus on specific sections of your work.&#10;📚 Enrich: Upload articles and documents to the Knowledge Base to ground the system's responses in your specific source material." style="cursor: help; color: #555; border-bottom: 1px dotted #777; font-size: 0.9em;">
                    ℹ️ How to use Lantern
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # --- NEW: Import / Export Buttons Moved Here ---
        c_io_1, c_io_2 = st.columns([1, 1])

        with c_io_1:
            with st.popover("📥 Import", use_container_width=True):
                uploaded_doc = st.file_uploader("Upload DOCX/PDF to replace content", type=["pdf", "docx", "txt", "md"],
                                                key="doc_import_right")
                if uploaded_doc:
                    file_ext = uploaded_doc.name.split('.')[-1].lower()
                    if file_ext not in ['pdf', 'docx']:
                        st.error("Error: File type not supported. Please upload a DOCX or PDF file.")
                    else:
                        if st.session_state.get("last_imported_doc") != uploaded_doc.name:
                            doc_text = extract_text_from_file(uploaded_doc)
                            if doc_text is not None:
                                escaped_text = html.escape(doc_text)
                                html_val = f"<p>{escaped_text.replace(chr(10), '<br>')}</p>"
                                st.session_state["editor_html"] = html_val
                                current_node.setdefault("metadata", {})["html"] = html_val
                                st.session_state.editor_version += 1
                                st.session_state["last_imported_doc"] = uploaded_doc.name
                                st.rerun()

        with c_io_2:
            with st.popover("📤 Export", use_container_width=True):
                export_text = current_node.get("metadata", {}).get("draft_plain", "")
                if not export_text and "editor_html" in st.session_state:
                    export_text = re.sub("<[^<]+?>", "", st.session_state["editor_html"]).strip()

                st.download_button(
                    label="📄 DOCX",
                    data=create_docx(export_text),
                    file_name="lantern_draft.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

                if HAS_REPORTLAB:
                    st.download_button(
                        label="📑 PDF",
                        data=create_pdf(export_text),
                        file_name="lantern_draft.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.warning("Install 'reportlab' for PDF")

        st.markdown(
            f'<div class="status-pill {mode_class}" style="margin: 5px 0; width: 100%; text-align: center;">State: {mode_label}</div>',
            unsafe_allow_html=True)
        st.divider()


        # 📌 Pinned Context Section (Always Visible)
        st.markdown("<div style='text-align: right; font-weight: bold; font-size: 1.1em; color: #334155; margin-bottom: 10px;'>📌 Pinned Context</div>", unsafe_allow_html=True)
        
        if st.session_state.tree["pinned_items"]:
            for i, item in enumerate(st.session_state.tree["pinned_items"]):
                is_node = isinstance(item, dict)
                p_text, p_title = (item.get("text", ""), item.get("title", "")) if is_node else (item, "")
                display_html = f"<strong>{p_title}</strong><br>{p_text}" if p_title else p_text
                c_txt, c_btns = st.columns([0.85, 0.15])
                with c_txt:
                    st.markdown(
                        f'<div class="pinned-box scrollable-content" style="max-height:150px;">{display_html}</div>',
                        unsafe_allow_html=True)
                with c_btns:
                    if st.button("❌", key=f"unpin_{i}", use_container_width=True):
                        st.session_state.tree["pinned_items"].pop(i);
                        st.rerun()
        else:
             st.markdown(
                """
                <div style="
                    background-color: #f8fafc; 
                    border: 1px solid #e2e8f0; 
                    border-radius: 6px; 
                    padding: 15px; 
                    text-align: center; 
                    color: #94a3b8; 
                    font-size: 0.9rem;">
                    No items pinned yet. Use "Pin" on suggestions to save context here.
                </div>
                """, 
                unsafe_allow_html=True
            )

        st.divider()

        # 💡 Critique logic (FIXED: Tooltip + Icon + Format)
        if "current_critiques" in st.session_state and st.session_state["current_critiques"]:
            c_head, c_clear = st.columns([0.8, 0.2])
            c_head.subheader("💡 Critical Perspective")
            if c_clear.button("🗑 Clear All", key="clear_all_critiques", use_container_width=True):
                st.session_state["current_critiques"] = []
                st.rerun()

            for i, item_data in enumerate(list(st.session_state["current_critiques"])):
                if isinstance(item_data, dict):
                    title = item_data.get("title", "Critique")
                    module = item_data.get("module", "Review")
                    text = item_data.get("text", "")
                else:
                    title = "Critique"
                    module = "Review"
                    text = item_data

                with st.container(border=True):
                    # ✅ FIXED: Title + Info Icon with Tooltip
                    st.markdown(
                        f'<b>{title}</b> '
                        f'<span title="Academic Principle: {module}" style="cursor: help; color: #64748b; font-size: 0.9em; margin-left: 5px;">ℹ️</span>',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<div class='suggestion-text scrollable-content'>{text}</div>",
                        unsafe_allow_html=True)

                    c_sel, c_pin, c_del = st.columns([1, 1, 1])
                    
                    with c_sel:
                         if st.button("✔ Select", key=f"cs_sel_{i}", help="Acknowledge this critique and strengthen your argument (Increments counter)", use_container_width=True):
                            # Add to persistent history (Increments Strengthened counter)
                            unique_key = text[:50]
                            if "bulletproof_history" not in st.session_state:
                                st.session_state.bulletproof_history = set()
                            st.session_state.bulletproof_history.add(unique_key)
                            
                            # Also Pin it
                            st.session_state.tree["pinned_items"].append({
                                "id": None,
                                "title": title,
                                "text": text,
                                "type": "critique"
                            })
                            st.session_state["current_critiques"].pop(i)
                            st.rerun()

                    with c_pin:
                        if st.button("📌 Pin", key=f"cs_pin_{i}", help="Pin to context without counting as strengthened", use_container_width=True):
                            st.session_state.tree["pinned_items"].append({
                                "id": None,
                                "title": title,
                                "text": text,
                                "type": "critique"
                            })
                            # User requested NOT to remove it from list when just pinning
                            st.rerun()

                    with c_del:
                        if st.button("🗑 Del", key=f"cs_del_{i}", use_container_width=True):
                            st.session_state["current_critiques"].pop(i)
                            st.rerun()
                            
        # 🌿 Suggested Paths
        if "dismissed_suggestions" not in st.session_state:
            st.session_state.dismissed_suggestions = set()

        visible_children = []
        for cid in current_node["children"]:
            if cid not in st.session_state.banned_ideas and \
               cid not in st.session_state.dismissed_suggestions and \
               not any(isinstance(p, dict) and p.get("id") == cid for p in st.session_state.tree["pinned_items"]):
                visible_children.append({"id": cid, "source": "Current"})

        if visible_children:
            c_head, c_clear = st.columns([0.8, 0.2])
            c_head.subheader("Suggested Paths")
            if c_clear.button("🗑 Clear All", key="clear_all_suggestions", use_container_width=True):
                 for child_id in [item["id"] for item in visible_children]:
                     st.session_state.dismissed_suggestions.add(child_id)
                 st.rerun()

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

                    # ✅ FIXED: Title + Info Icon with Tooltip
                    st.markdown(
                        f'<b>{title}</b> '
                        f'<span title="Academic Principle: {module_tag}" style="cursor: help; color: #64748b; font-size: 0.9em; margin-left: 5px;">ℹ️</span>',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f'''
                        <div class="scrollable-content">
                            {explanation}
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )

                    st.divider()
                    c_sel, c_pin, c_pru = st.columns([1, 1, 1])
                    with c_sel:
                        if st.button("✔ Select", key=f"s_{cid}", help=f"Select this path based on Academic Principle: {module_tag}",
                                     use_container_width=True):
                            pin_obj = {"id": cid, "title": title, "text": explanation, "type": "idea"}
                            st.session_state.tree["pinned_items"].append(pin_obj)

                            child.setdefault("metadata", {})["label"] = title
                            child.setdefault("metadata", {})["explanation"] = explanation
                            child.setdefault("metadata", {})["html"] = current_node.get("metadata", {}).get("html", "")
                            child["metadata"]["selected_path"] = True

                            # --- Automatic Sibling Dismissal ---
                            # Every sibling of the selected node that is currently a suggestion should be dismissed.
                            for sibling_id in current_node["children"]:
                                if sibling_id != cid:
                                    st.session_state.dismissed_suggestions.add(sibling_id)

                            navigate_to_node(tree, cid);
                            st.rerun()
                    with c_pin:
                        if st.button("📌 Pin", key=f"p_{cid}", help="Pin this suggestion to the sidebar for future reference", use_container_width=True):
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
                        st.session_state["last_refine_context"] = payload.get("context", {})
                except Exception as e:
                    st.error(f"❌ Gemini Error: {e}")
                finally:
                    st.session_state.llm_in_flight = False
                    st.session_state.pending_action = None
                    st.session_state.is_thinking = False
                    st.rerun()


if __name__ == "__main__":
    main()