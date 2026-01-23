import streamlit as st
import base64
from streamlit_quill import st_quill
import re
import json
import os

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
# Persistence Helpers
# -------------------------------------------------
AUTOSAVE_FILE = "lantern_autosave.json"

def save_autosave(tree):
    """Saves the current tree state to a local JSON file."""
    try:
        with open(AUTOSAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Auto-save failed: {e}")

def load_autosave():
    """Traies to load the tree state from the local autosave file."""
    if not os.path.exists(AUTOSAVE_FILE):
        return False
    try:
        with open(AUTOSAVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        st.session_state.tree = data
        # Ensure migration
        if "pinned_items" not in st.session_state.tree:
             st.session_state.tree["pinned_items"] = []
        return True
    except Exception as e:
        st.error(f"Failed to load autosave: {e}")
        return False

def save_project(tree):
    return json.dumps(tree, indent=2, ensure_ascii=False)


def load_project(json_str):
    try:
        data = json.loads(json_str)
        st.session_state.tree = data
        # Migrate old projects or ensure key exists
        if "pinned_items" not in st.session_state.tree:
             st.session_state.tree["pinned_items"] = []
             
        st.session_state.banned_ideas = []
        save_autosave(st.session_state.tree) # Save immediately after loading
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
    
    # Map node type to status labels
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
    
    # Strict Root Initialization Flag
    if "root_topic_resolved" not in st.session_state:
        st.session_state.root_topic_resolved = False

    # Concurrency Lock
    if "llm_in_flight" not in st.session_state:
        st.session_state.llm_in_flight = False

    if "tree" not in st.session_state:
        if not load_autosave():
           st.session_state.tree = init_tree("")
           save_autosave(st.session_state.tree)
    
    # Ensure pinned_items exists in tree (migration for active session)
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

    # --- Interactive Navigation Handler (Native Selectbox) ---
    # Navigation is now handled by 'handle_navigation' callback in sidebar_map.py
    # No URL query params are used.




    tree = st.session_state.tree
    current_node = get_current_node(tree)
    mode_label, mode_class = get_ui_state(tree)

    # Create Columns (Left: Editor, Right: Lantern Context)
    col_editor, col_lantern = st.columns([2, 1], gap="large")

    # ==========================================
    # LEFT COLUMN: EDITOR
    # ==========================================
    with col_editor:
        if "comparison_data" in st.session_state:
            st.subheader("⚖️ Branch Comparison")
            comp = st.session_state.comparison_data
            st.markdown(f"**Comparing:** `{comp['a']['summary'][:20]}...` vs `{comp['b']['summary'][:20]}...`")
            
            diff_html = generate_diff_html(comp['a']['summary'], comp['b']['summary'])
            st.markdown(f'<div style="background-color: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; line-height: 1.6;">{diff_html}</div>', unsafe_allow_html=True)
            
        else:
            st.subheader("Editor")

        st.markdown(
            """
            <div class="action-bar">
                <div class="action-bar-title">AI Reasoning Actions</div>
            """,
            unsafe_allow_html=True
        )

        # --- Navigation / Undo ---
        # (Button Removed per user request)

        
        if "editor_html" not in st.session_state:
            st.session_state["editor_html"] = current_node.get("metadata", {}).get("html", "")

        st.session_state.setdefault("focused_text", current_node.get("summary", ""))

        c1, c2, c3 = st.columns([1, 1, 1], gap="small")

        with c1:
            if st.button("🌱 Expand", help="Explore new angles and expand thinking", use_container_width=True):
                st.session_state.pending_action = {
                    "action": ActionType.DIVERGE,
                    "user_text": st.session_state["focused_text"],
                }
                st.session_state.is_thinking = True
                st.rerun()

        with c2:
            if st.button("⚖️ Critique", help="Challenge arguments and find weaknesses", use_container_width=True):
                st.session_state.pending_action = {
                    "action": ActionType.CRITIQUE,
                    "user_text": st.session_state["focused_text"],
                }
                st.session_state.is_thinking = True
                st.rerun()

        with c3:
            if st.button("✨ Refine", help="Improve clarity and structure without changing ideas", use_container_width=True):
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

        # Safeguard: If HTML is missing but Summary exists, backfill it to prevent data loss or empty editor.
        if "html" not in current_node.get("metadata", {}) or not current_node["metadata"]["html"]:
             if current_node.get("summary"):
                 current_node.setdefault("metadata", {})["html"] = f"<p>{current_node['summary'].replace(chr(10), '<br>')}</p>"

        if "last_refine_diff" in st.session_state:
             # --- Review Mode (Refine) ---
             st.info("✨ AI Suggested Improvements (Review Mode)")
             
             # Show Diff
             st.markdown(
                 f'<div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.9rem; line-height: 1.6; color: #334155; margin-bottom: 10px;">{st.session_state["last_refine_diff"]}</div>',
                 unsafe_allow_html=True
             )
             
             c_accept, c_discard = st.columns([1, 1])
             with c_accept:
                 if st.button("✅ Accept Changes", use_container_width=True, type="primary"):
                     # Apply changes
                     new_text = st.session_state["last_refine_text"]
                     st.session_state["editor_html"] = new_text
                     current_node.setdefault("metadata", {})["html"] = new_text
                     
                     # Clean up
                     del st.session_state["last_refine_diff"]
                     del st.session_state["last_refine_text"]
                     st.session_state.pop("last_refine_original_target", None)
                     
                     save_autosave(st.session_state.tree)
                     st.rerun()
                     
             with c_discard:
                 if st.button("❌ Discard", use_container_width=True):
                     # Clean up
                     del st.session_state["last_refine_diff"]
                     del st.session_state["last_refine_text"]
                     st.session_state.pop("last_refine_original_target", None)
                     st.rerun()
                     
             # Placeholder to keep UI stable
             html_content = st.session_state["editor_html"]

        else:
            # --- Standard Editor Mode ---
            html_content = st_quill(
                value=st.session_state["editor_html"],
                placeholder="Start drafting your thoughts here...",
                html=True,
                toolbar=[
                    ["bold", "italic", "underline", "strike"],
                    [{"header": [1, 2, 3, False]}],
                    [{"list": "ordered"}, {"list": "bullet"}],
                    ["link", "image", "blockquote", "code-block"],
                    ["clean"],
                ],
                key=f"quill_main_{st.session_state.editor_version}",
            )

        blocks_data = []
        plain_text = ""  # Initialize to prevent UnboundLocalError
        if html_content:
            # Update the persistent editor state
            st.session_state["editor_html"] = html_content
            # Keep the current node's draft synced without destroying its Title (summary)
            current_node.setdefault("metadata", {})["html"] = html_content
            
            # --- Extract Plain Text for Focus Logic ONLY (Do not overwrite summary) ---
            text_processing = re.sub(r"<(/?p|/?div|/h[1-6])>", "\n\n", html_content)
            text_processing = text_processing.replace("<br>", "\n")
            plain_text = re.sub("<[^<]+?>", "", text_processing).strip()
            plain_text = re.sub(r"\n{3,}", "\n\n", plain_text)
            
            # Store the current draft's plain text in metadata for context retrieval
            current_node["metadata"]["draft_plain"] = plain_text
            # Note: We NO LONGER overwrite current_node["summary"] here.
            # Summary = The Idea/Title. Metadata['html'] = The Draft.
            
            # --- Auto-Detect Topic for Root Node (One-Time Strict Lock) ---
            # Correct Flow: Resolve -> Lock -> Never touch again
            if not st.session_state.get("root_topic_resolved", False):
                if current_node["type"] == "root":
                     # 1. Check for H1 (Priority 1)
                     h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_content, re.IGNORECASE | re.DOTALL)
                     if h1_match:
                         title_text = re.sub("<[^<]+?>", "", h1_match.group(1)).strip()
                         if title_text:
                             current_node["summary"] = title_text
                             st.session_state.root_topic_resolved = True # LOCKED
                             save_autosave(st.session_state.tree)
                             st.rerun()
                     
                     # 2. Fallback to AI Summarization (Priority 2)
                     elif len(plain_text) > 50:
                         from llm_client import call_llm 
                         try:
                             topic = call_llm(f"Summarize the following text into a very short, 3-6 word academic topic title. Do not use quotes or prefixes:\n\n{plain_text}")
                             if topic:
                                 current_node["summary"] = topic.strip()
                                 st.session_state.root_topic_resolved = True # LOCKED
                                 save_autosave(st.session_state.tree)
                                 st.rerun()
                         except Exception:
                             pass
            # -----------------------------------------------------------------
            
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
            # Fix: Use the full draft content, NOT the Summary/Title
            st.session_state["focused_text"] = current_node.get("metadata", {}).get("draft_plain", plain_text)

        with st.expander("🔍 AI Focus Preview", expanded=False):
            st.text_area("", value=st.session_state["focused_text"], height=100, disabled=True)

    # ==========================================
    # SIDEBAR TOOLS
    # ==========================================
    # --- Map Tree (Stays in sidebar) ---
    render_sidebar_map(tree)
    
    with st.sidebar.expander("⚖️ Compare Branches", expanded=False):
        st.caption("Select two nodes to see a visual side-by-side diff.", help="Choose any two ideas from your history to see how they differ.")
        all_nodes = list(tree["nodes"].values())
        format_func = lambda n: f"{n['summary'][:40]}... ({n['type']})"
        node_a = st.selectbox("Node A", all_nodes, format_func=format_func, index=all_nodes.index(get_current_node(tree)), key="cmp_a", help="Select the first idea to compare (defaults to current).")
        node_b = st.selectbox("Node B", all_nodes, format_func=format_func, index=0, key="cmp_b", help="Select the second idea to compare against.")
        if st.sidebar.button("Compare Ideas", help="Launch the comparison view to see exactly what changed."):
            st.session_state.comparison_data = {"a": node_a, "b": node_b}
            st.rerun()

    if st.session_state.get("comparison_data"):
        if st.sidebar.button("Close Comparison"):
            del st.session_state["comparison_data"]
            st.rerun()

    # ==========================================
    # RIGHT COLUMN: INTERACTION & CONTEXT
    # ==========================================
    with col_lantern:
        # --- Branding (Logo + Guide + Status) ---
        if logo_base64:
            st.markdown(
                f'<div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 5px;">'
                f'<img src="data:image/jpeg;base64,{logo_base64}" style="width: 70px; opacity: 0.9;"></div>',
                unsafe_allow_html=True
            )
        
        st.markdown(f'<div class="status-pill {mode_class}" style="margin: 5px 0; width: 100%; text-align: center;">State: {mode_label}</div>', unsafe_allow_html=True)
        st.divider()

        # --- Project Management ---
        with st.expander("📁 Project Management", expanded=False):
            st.download_button("📥 Export Project (JSON)", data=save_project(tree), file_name="lantern_project.json",
                               mime="application/json", use_container_width=True)
            uploaded_proj = st.file_uploader("📤 Load Project", type="json", key="proj_loader")
            if uploaded_proj:
                if load_project(uploaded_proj.getvalue().decode("utf-8")):
                    st.success("Loaded!");
                    st.rerun()

        # --- Knowledge Base (New File Upload) ---
        with st.expander("📚 Knowledge Base", expanded=False):
            st.caption("Upload reference files (txt, md) to provide more context to the AI.")
            uploaded_files = st.file_uploader("Upload reference files", type=["txt", "md"], accept_multiple_files=True, key="kb_uploader")
            
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    if uploaded_file.name not in st.session_state.knowledge_base:
                        st.session_state.knowledge_base[uploaded_file.name] = uploaded_file.getvalue().decode("utf-8")
                
                # Show active files
                if st.session_state.knowledge_base:
                    st.markdown("**Active Files:**")
                    for fname in list(st.session_state.knowledge_base.keys()):
                        col_f, col_d = st.columns([0.8, 0.2])
                        col_f.text(f"📄 {fname}")
                        if col_d.button("🗑️", key=f"del_{fname}"):
                            del st.session_state.knowledge_base[fname]
                            st.rerun()

        # --- About Lantern ---
        with st.expander("ℹ️ About Lantern", expanded=False):
            st.markdown(
                """
                **Lantern** is an AI thinking partner designed to enhance your cognitive autonomy. Unlike typical AI that does the work for you, Lantern scaffolds your reasoning.

                **Core Philosophy:**
                - **You Lead:** You write drafts and make final decisions.
                - **AI Supports:** It suggests angles, critiques logic, and refines clarity.

                **Tools:**
                - **🌱 Expand:** Break writer's block with diverse perspectives.
                - **⚖️ Critique:** Strengthen arguments by finding logical gaps.
                - **✨ Refine:** Polish clarity while keeping your voice.
                - **🗺️ Tree:** Navigate your history and explore alternative paths.
                """
            )
        

        # 📌 Pinned Context Section
        if st.session_state.tree["pinned_items"]:
            st.markdown("<br><b>📌 Pinned Context</b>", unsafe_allow_html=True)
            for i, item in enumerate(st.session_state.tree["pinned_items"]):
                # Handle both old (string) and new (dict) structures
                is_node = isinstance(item, dict)
                
                # Default values for text/display
                p_text = item if not is_node else item.get("text", "")
                p_title = item.get("title", "") if is_node else ""
                
                # Render Rich Context if available
                display_html = ""
                if p_title and p_title != p_text:
                     # Structured Object (New)
                     display_html = f"<strong>{p_title}</strong><br><span style='font-size:0.9em; opacity:0.9'>{p_text}</span>"
                else:
                     # Legacy or unstructured
                     display_html = p_text

                c_txt, c_btns = st.columns([0.85, 0.15])
                with c_txt:
                    st.markdown(f'<div class="pinned-box">{display_html}</div>', unsafe_allow_html=True)
                with c_btns:
                    if st.button("❌", key=f"unpin_{i}", help="Remove from context", use_container_width=True):
                        st.session_state.tree["pinned_items"].pop(i)
                        save_autosave(st.session_state.tree)
                        st.rerun()
                
                # Buttons Row: Expanded Controls (Removed "Explore", kept minimal)
                if is_node:
                    pass # We auto-explore below in Suggested Paths now. Logic is simpler.
                else:
                    # Legacy string pin support (Concept only) - can keep or remove, user didn't complain about this explicitly but asked to cancel "Added exploring button"
                    if st.button("➕ Turn into Node", key=f"make_node_{i}", help="Convert text to a node to explore it", use_container_width=True):
                        from tree import add_child
                        clean_summary = p_text.replace("**", "").replace("Critique: ", "").replace("Suggestion: ", "")
                        target_id = add_child(tree, current_node["id"], clean_summary, node_type="standard")
                        tree["nodes"][target_id].setdefault("metadata", {})["html"] = st.session_state["editor_html"]
                        st.session_state.tree["pinned_items"][i] = {"id": target_id, "text": p_text} # Upgrade pin
                        save_autosave(st.session_state.tree)
                        st.rerun()


            if st.button("Clear all context", help="Wipe all pinned items"):
                st.session_state.tree["pinned_items"] = []
                st.session_state.selected_paths = []
                st.session_state.banned_ideas = []
                save_autosave(st.session_state.tree)
                st.rerun()

        st.divider()

        # 💡 Critique Result (OUTSIDE Pinned Context Block)
        if "current_critiques" in st.session_state and st.session_state["current_critiques"]:
            st.subheader("💡 Critical Perspective")
            
            # Special case for "No Critique"
            if st.session_state["current_critiques"][0] == "NO_CRITIQUE_NEEDED":
                st.info("✨ Lantern finds your current draft rigorous and logically sound. No critical gaps identified.")
                if st.button("Dismiss", key="dismiss_none"):
                    del st.session_state["current_critiques"]
                    st.rerun()
            else:
                if st.button("Dismiss All", help="Clear all suggestions"):
                    del st.session_state["current_critiques"]
                    st.rerun()

                # Iterate through all available critiques
                # "current_critiques" now contains dicts: {"id": "...", "text": "..."}
                for i, item_data in enumerate(list(st.session_state["current_critiques"])):
                    # Handle both old (str) and new (dict) formats for safety
                    if isinstance(item_data, dict):
                        critique_text = item_data["text"]
                        critique_id = item_data["id"]
                    else:
                        critique_text = item_data
                        critique_id = None # Should not happen with new controller logic
                        
                    with st.container(border=True):
                        # Parse Title vs Content
                        title_text = "Critical Perspective"
                        body_text = critique_text
                        
                        if "Title:" in critique_text and "Critique:" in critique_text:
                            try:
                                parts = critique_text.replace("Title:", "").split("Critique:", 1)
                                title_text = parts[0].strip(" *")
                                body_text = parts[1].strip()
                            except:
                                pass
                        
                        # Meta
                        st.markdown(
                            f'''
                            <div class="suggestion-meta">
                                <span>⚖️ Critique</span>
                                <span>AI Generated</span>
                            </div>
                            ''',
                            unsafe_allow_html=True
                        )
                        
                        st.markdown(f"**{title_text}**")
                        st.markdown(f"<div class='suggestion-text'>{body_text}</div>", unsafe_allow_html=True)
                        
                        st.divider()
                        
                        c_sel, c_pin, c_ign = st.columns([1, 1, 1])
                        with c_sel:
                            # Button acts as "Navigate" since node exists
                            if st.button("✔ Select", key=f"cs_sel_{i}", help="Pivot your focus to this critique", use_container_width=True):
                                if critique_id:
                                    # Copy current state to the critique node if needed
                                    critique_node = tree["nodes"][critique_id]
                                    # Inherit clean HTML from parent
                                    parent_html = current_node.get("metadata", {}).get("html", "")
                                    if not parent_html and current_node["summary"]:
                                        parent_html = f"<p>{current_node['summary']}</p>"
                                    
                                    critique_node.setdefault("metadata", {})["html"] = parent_html
                                    
                                    # Auto-Pin and Navigate
                                    st.session_state.tree["pinned_items"].append({"id": critique_id, "text": f"**Critique: {title_text}**\n\n{body_text}"})
                                    st.session_state.selected_paths.append(critique_id)
                                    
                                    
                                    navigate_to_node(tree, critique_id)
                                    save_autosave(st.session_state.tree)
                                    st.rerun()
                                    
                        with c_pin:
                            if st.button("📌 Pin", key=f"cp_{i}", help="Add to reference context without pivoting", use_container_width=True):
                                st.session_state.tree["pinned_items"].append({"id": critique_id, "text": f"**Critique: {title_text}**\n\n{body_text}"})
                                # REMOVE from list so it disappears
                                st.session_state["current_critiques"].pop(i)
                                save_autosave(st.session_state.tree)
                                st.rerun()
                        with c_ign:
                            if st.button("🗑 Del", key=f"ci_{i}", help="Dismiss this specific suggestion", use_container_width=True):
                                st.session_state["current_critiques"].pop(i)
                                st.rerun()
            st.divider()

        # (Old Refine UI removed - now handled in Editor Review Mode)
            
            st.caption("Review and edit the suggestion below before applying:")
            
            # --- Interactive Editing ---
            refined_editable = st.text_area(
                "Proposed Text", 
                value=st.session_state.get("last_refine_text", ""), 
                height=250,
                key="refine_editor"
            )
            
            c_apply, c_dismiss = st.columns([1, 1])
            with c_apply:
                if st.button("Apply Change", help="Apply this improvement to the editor"):
                    if refined_editable:
                        # Logic: Are we replacing the WHOLE text or just a BLOCK?
                        # We use 'last_refine_original_target' to know what was sent to LLM.
                        original_target = st.session_state.get("last_refine_original_target", "")
                        full_current_text = current_node["summary"]
                        
                        # 1. If original target matches full text -> Full Replace
                        if not original_target or original_target.strip() == full_current_text.strip():
                             final_text = refined_editable
                        
                        # 2. Block Replace (Smart Patch)
                        else:
                             # Try fuzzy match to find the block in the current full text
                             patched_text = apply_fuzzy_replacement(full_current_text, original_target, refined_editable)
                             
                             if patched_text:
                                 final_text = patched_text
                             else:
                                 # Fallback: simple replace (might fail if user edited meantime)
                                 if original_target in full_current_text:
                                     final_text = full_current_text.replace(original_target, refined_editable, 1)
                                 else:
                                     st.error("Could not find the original text block to replace. It might have been modified.")
                                     st.stop()
                        
                        # Update Node
                        current_node["summary"] = final_text
                        current_node.setdefault("metadata", {})["html"] = f"<p>{final_text.replace(chr(10), '<br>')}</p>"
                        st.session_state["focused_text"] = final_text # Update focus to new text
                        
                        # Cleanup
                        del st.session_state["last_refine_diff"]
                        del st.session_state["last_refine_text"]
                        st.session_state.pop("last_refine_original_target", None)
                        
                        # Force Editor Refresh
                        st.session_state.editor_version += 1
                        st.rerun()
                        
            with c_dismiss:
                if st.button("Dismiss Refinement"):
                    del st.session_state["last_refine_diff"]
                    st.session_state.pop("last_refine_text", None)
                    st.session_state.pop("last_refine_original_target", None)
                    st.rerun()
            st.divider()

        # 🌿 Suggested Paths
        def is_intro_like(text: str) -> bool:
            return (
                    "להלן" in text
                    and "הצעות" in text
                    and len(text) < 250
            )

        # --- LOGIC: MERGE Current & Pinned Suggestions ---
        # 1. Current Node Children
        visible_children = []
        seen_ids = set()

        # Add current node children FIRST
        for cid in current_node["children"]:
            if cid in st.session_state.banned_ideas: continue
            # ❌ Hide if already pinned
            if any(isinstance(p, dict) and p.get("id") == cid for p in st.session_state.tree["pinned_items"]): continue
            
            seen_ids.add(cid)
            visible_children.append({"id": cid, "source": "Current", "source_id": current_node["id"]})

        # 2. Pinned Nodes Children (The "Exposed Level" requested)
        for item in st.session_state.tree["pinned_items"]:
            if isinstance(item, dict) and item.get("id"):
                 p_id = item["id"]
                 if p_id in tree["nodes"]:
                     p_node = tree["nodes"][p_id]
                     for cid in p_node["children"]:
                         if cid in st.session_state.banned_ideas: continue
                         if cid in seen_ids: continue # Avoid dupes
                         if any(isinstance(p, dict) and p.get("id") == cid for p in st.session_state.tree["pinned_items"]): continue

                         seen_ids.add(cid)
                         visible_children.append({"id": cid, "source": "Pinned Idea", "source_id": p_id})

        # Filter intro-like text
        final_list = []
        for item in visible_children:
            text = tree["nodes"][item["id"]]["summary"]
            if not is_intro_like(text):
                final_list.append(item)

        if final_list:
            # (Divider removed to prevent double-lines after Critique section)
            st.subheader("Suggested Paths")
            st.caption(
                "Lantern generated alternative reasoning paths from your current draft and pinned ideas."
                "Select one to continue."
            )

            # --- Layout: Vertical List (Compact) ---
            for item in final_list:
                cid = item["id"]
                source_label = item["source"]
                child = tree["nodes"][cid]
                
                with st.container(border=True):
                    # Meta + Text
                    st.markdown(
                        f'''
                        <div class="suggestion-meta">
                            <span>🤖 {child.get("type", "Idea")}</span>
                            <span>From: {source_label}</span>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
                    
                    # Formatting Title vs Content
                    raw_text = child["summary"]
                    title_clean = raw_text
                    body_clean = ""
                    is_structured = False

                    # Try to separate Title/Explanation
                    if "Title:" in raw_text:
                        # Normalize splitting
                        if "Explanation:" in raw_text:
                            parts = raw_text.replace("Title:", "").split("Explanation:", 1)
                        else:
                            parts = raw_text.replace("Title:", "").split("\n", 1)

                        if len(parts) >= 2:
                            title_clean = parts[0].strip(" *")
                            body_clean = parts[1].strip()
                            is_structured = True

                    if is_structured:
                        st.markdown(f"**{title_clean}**")
                        
                        # Truncate body if too long (Preview Mode)
                        display_body = body_clean
                        if len(display_body) > 300:
                             display_body = display_body[:290] + "..."
                             
                        st.markdown(f"<div style='font-size: 0.9em; color: #475569;'>{display_body}</div>", unsafe_allow_html=True)
                        formatted_text_for_pin = f"**{title_clean}**\n{get_node_short_label(child)}"
                    else:
                        # Truncate raw text
                        display_text = raw_text
                        if len(display_text) > 300:
                             display_text = display_text[:290] + "..."
                             
                        st.markdown(f"<div class='suggestion-text'>{display_text}</div>", unsafe_allow_html=True)
                        formatted_text_for_pin = get_node_short_label(child)

                    st.divider()

                    # Buttons Row (Horizontal)
                    c_sel, c_pin, c_pru = st.columns([1, 1, 1])

                    # ✅ SELECT
                    with c_sel:
                        if st.button(
                                "✔ Select",
                                key=f"s_{cid}",
                                help="Commit this idea without changing your text",
                                use_container_width=True
                        ):
                             # ... logic ...
                            st.session_state.selected_paths.append(cid)
                            
                            # Use STRUCTURED OBJECT for context (Task 2: Pinning Structure)
                            full_text_pin = child.get("metadata", {}).get("idea_text", formatted_text_for_pin)
                            pin_obj = {
                                "id": cid,
                                "title": title_clean if is_structured else child["summary"],
                                "text": full_text_pin,
                                "type": "idea"
                            }
                            st.session_state.tree["pinned_items"].append(pin_obj)
                            
                            # --- Fix for Text Loss: Inherit Parent Content ---
                            # 1. Save the original "Idea" as the label for the Tree visualization
                            child.setdefault("metadata", {})["label"] = title_clean if is_structured else child["summary"][:30]
                            
                            # 2. Merge Parent Text ONLY (Do not touch editor with AI text)
                            parent_html = current_node.get("metadata", {}).get("html", "")
                            # If parent has no HTML but has summary, wrap it
                            if not parent_html and current_node["summary"]:
                                parent_html = f"<p>{current_node['summary']}</p>"
                                
                            # STRICT Inheritance: Editor stays exactly as it was
                            child.setdefault("metadata", {})["html"] = parent_html
                            # (Removed child["summary"] = current_node["summary"] - Keep child's own title)
                            
                            # (Sibling Cleanup Removed - User Request: Keep alternatives visible)


                            st.session_state.pop("current_critiques", None)
                            st.session_state.pop("last_refine_diff", None)
                            
                            # Navigate to the selected node to deepen the tree
                            navigate_to_node(tree, cid)
                            save_autosave(st.session_state.tree)
                            st.rerun()

                    # 📌 PIN
                    with c_pin:
                        if st.button("📌 Pin", key=f"p_{cid}", help="Keep this idea as context", use_container_width=True):
                            full_text_pin = child.get("metadata", {}).get("idea_text", formatted_text_for_pin)
                            pin_obj = {
                                "id": cid,
                                "title": title_clean if is_structured else child["summary"],
                                "text": full_text_pin,
                                "type": "idea"
                            }
                            st.session_state.tree["pinned_items"].append(pin_obj)
                            save_autosave(st.session_state.tree)
                            st.rerun()

                    # ✂️ PRUNE
                    with c_pru:
                        if st.button("🗑 Del", key=f"pr_{cid}", help="Discard this idea", use_container_width=True):
                            st.session_state.banned_ideas.append(cid)
                            st.rerun()

        # -------------------------------------------------
        # Execute pending Lantern action (non-blocking UX)
        # -------------------------------------------------
        if st.session_state.pending_action and st.session_state.is_thinking:
            # --- Concurrency Guard ---
            if st.session_state.llm_in_flight:
                st.warning("⚠️ Lantern is already thinking... (Concurrency Guard Triggered)")
                st.stop()
            
            st.session_state.llm_in_flight = True
            
            try:
                payload = st.session_state.pending_action
                response = handle_event(
                    st.session_state.tree,
                    UserEventType.ACTION,
                    {
                        "action": payload["action"],
                        "pinned_context": st.session_state.tree["pinned_items"],
                        "banned_ideas": st.session_state.banned_ideas,
                        "user_text": payload["user_text"],
                        "knowledge_base": st.session_state.get("knowledge_base", {}),
                    }
                )

                if payload["action"] == ActionType.CRITIQUE:
                    st.session_state["current_critiques"] = response.get("items", [])

                elif payload["action"] == ActionType.REFINE:
                    st.session_state["last_refine_diff"] = response.get("diff_html")
                    st.session_state["last_refine_text"] = response.get("refined_text")
                    st.session_state["last_refine_original_target"] = payload["user_text"]
                    st.session_state.pop("refine_changes", None)

            except Exception as e:
                st.error(f"❌ Gemini Error: {e}")
                st.session_state.pending_action = None
                st.session_state.is_thinking = False
                st.session_state.llm_in_flight = False # Release lock on error
                st.stop()
                
            finally:
                st.session_state.llm_in_flight = False # Always release lock

            # DIVERGE → Children added by controller
            st.session_state.pending_action = None
            st.session_state.is_thinking = False
            save_autosave(st.session_state.tree)
            st.rerun()


if __name__ == "__main__":
    main()