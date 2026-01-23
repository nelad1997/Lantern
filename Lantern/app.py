import streamlit as st
import base64
from streamlit_quill import st_quill
import re
import json

# --- Imports ---
from definitions import UserEventType, ActionType
from tree import init_tree, get_current_node, navigate_to_node
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
    if "editor_version" not in st.session_state:
        st.session_state.editor_version = 0
    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = {}

    # --- Interactive Navigation Handler (Map Click) ---
    if "node_id" in st.query_params:
        target_node_id = st.query_params["node_id"]
        if target_node_id in st.session_state.tree["nodes"]:
            # Perform Navigation
            navigate_to_node(st.session_state.tree, target_node_id)
            
            # Auto-Pin for context
            target_node = st.session_state.tree["nodes"][target_node_id]
            if not any(item.get("id") == target_node_id for item in st.session_state.pinned_context):
                st.session_state.pinned_context.append({
                    "id": target_node_id, 
                    "text": target_node["summary"]
                })
            
            # Clear query params to prevent reload loop
            st.query_params.clear()
            st.rerun()


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
        if current_node.get("parent"):
             if st.button("↩ Go to Parent (Undo)", help="Go back to the previous thought"):
                 navigate_to_node(tree, current_node["parent"])
                 st.rerun()
        
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

        html_content = st_quill(
            value=st.session_state["editor_html"],
            placeholder="Start drafting your thoughts here...",
            html=True,
            toolbar=[
                ["bold", "italic", "underline"],
                [{"header": [1, 2, 3, False]}],
                [{"list": "ordered"}, {"list": "bullet"}],
            ],
            key=f"quill_main_{st.session_state.editor_version}",
        )

        blocks_data = []
        if html_content is not None:
            st.session_state["editor_html"] = html_content
            # Optionally keep the current node synced if it's the main path
            current_node.setdefault("metadata", {})["html"] = html_content
            
            # --- Better HTML Parsing (Preserve Paragraphs & Headers) ---
            # 1. Replace block endings with double newlines
            text_processing = re.sub(r"<(/?p|/?div|/h[1-6])>", "\n\n", html_content)
            # 2. Handle line breaks
            text_processing = text_processing.replace("<br>", "\n")
            # 3. Strip remaining tags
            plain_text = re.sub("<[^<]+?>", "", text_processing).strip()
            # 4. Clean excessive newlines (max 2)
            plain_text = re.sub(r"\n{3,}", "\n\n", plain_text)
            
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
        if st.session_state.pinned_context:
            st.markdown("<br><b>📌 Pinned Context</b>", unsafe_allow_html=True)
            for i, item in enumerate(st.session_state.pinned_context):
                # Handle both old (string) and new (dict) structures
                is_node = isinstance(item, dict)
                p_text = item["text"] if is_node else item
                p_id = item["id"] if is_node else None

                c_txt, c_btns = st.columns([0.85, 0.15])
                with c_txt:
                    st.markdown(f'<div class="pinned-box">{p_text}</div>', unsafe_allow_html=True)
                with c_btns:
                    if st.button("❌", key=f"unpin_{i}", help="Remove from context", use_container_width=True):
                        st.session_state.pinned_context.pop(i)
                        st.rerun()
                
                # Show Select button BELOW the box if it's not the current node
                if p_id != tree["current"]:
                    c_s1, c_s2 = st.columns([1, 1])
                    with c_s1:
                        if st.button("✔ Focus AI", key=f"sel_p_{i}", help="Direct AI's focus to this idea", use_container_width=True):
                            target_id = p_id
                            if not target_id:
                                from tree import add_child
                                clean_summary = p_text.replace("**", "").replace("Critique: ", "").replace("Suggestion: ", "")
                                target_id = add_child(tree, current_node["id"], clean_summary, node_type="standard")
                                tree["nodes"][target_id].setdefault("metadata", {})["html"] = st.session_state["editor_html"]
                                st.session_state.pinned_context[i]["id"] = target_id
                            
                            st.session_state.selected_paths = [target_id]
                            navigate_to_node(tree, target_id)
                            st.rerun()
                    
                    with c_s2:
                        if p_id: # Only show restore for identified nodes
                            if st.button("⏪ Restore Text", key=f"res_p_{i}", help="OVERWRITE current editor with this historical version", use_container_width=True):
                                node_to_restore = tree["nodes"][p_id]
                                st.session_state["editor_html"] = node_to_restore.get("metadata", {}).get("html", "")
                                if "editor_version" in st.session_state:
                                    st.session_state.editor_version += 1
                                st.rerun()

            if st.button("Clear all context", help="Wipe all pinned items"):
                st.session_state.pinned_context = []
                st.session_state.selected_paths = []
                st.session_state.banned_ideas = []
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
                for i, item in enumerate(list(st.session_state["current_critiques"])):
                    with st.container(border=True):
                        # Parse Title vs Content
                        title_text = "Critical Perspective"
                        body_text = item
                        
                        if "Title:" in item and "Critique:" in item:
                            try:
                                parts = item.replace("Title:", "").split("Critique:", 1)
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
                            if st.button("✔ Select", key=f"cs_sel_{i}", help="Accept this critique and pivot your focus here", use_container_width=True):
                                # 1. Create Tree Node
                                from tree import add_child
                                child_id = add_child(tree, current_node["id"], body_text, node_type="critique")
                                child = tree["nodes"][child_id]
                                
                                # 2. Inherit HTML (Clean)
                                parent_html = current_node.get("metadata", {}).get("html", "")
                                if not parent_html and current_node["summary"]:
                                    parent_html = f"<p>{current_node['summary']}</p>"
                                
                                child.setdefault("metadata", {})["html"] = parent_html
                                child["metadata"]["label"] = title_text 
                                child["summary"] = f"{title_text}: {body_text}"
                                
                                # 3. Pin & Navigate (Preseve context as requested)
                                st.session_state.pinned_context.append({"id": child_id, "text": f"**Critique: {title_text}**\n\n{body_text}"})
                                st.session_state.selected_paths.append(child_id)
                                
                                # 4. REMOVE from list so it disappears
                                st.session_state["current_critiques"].pop(i)
                                
                                navigate_to_node(tree, child_id)
                                if "editor_version" in st.session_state:
                                    st.session_state.editor_version += 1
                                st.rerun()
                                
                        with c_pin:
                            if st.button("📌 Pin", key=f"cp_{i}", help="Add to reference context without pivoting", use_container_width=True):
                                st.session_state.pinned_context.append({"id": None, "text": f"**Critique: {title_text}**\n\n{body_text}"})
                                # REMOVE from list so it disappears
                                st.session_state["current_critiques"].pop(i)
                                st.rerun()
                        with c_ign:
                            if st.button("🗑 Del", key=f"ci_{i}", help="Dismiss this specific suggestion", use_container_width=True):
                                st.session_state["current_critiques"].pop(i)
                                st.rerun()
            st.divider()

        # ✨ Refined Changes (Full Text / Block Diff)
        if "last_refine_diff" in st.session_state:
            st.subheader("✨ Refined Suggestion")
            
            # Show Diff
            st.markdown(
                f'<div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.9rem;">{st.session_state["last_refine_diff"]}</div>',
                unsafe_allow_html=True)
            
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

        visible_children = []
        for cid in current_node["children"]:
            if cid in st.session_state.banned_ideas:
                continue

            # ❌ Hide if already pinned
            if any(isinstance(p, dict) and p.get("id") == cid for p in st.session_state.pinned_context):
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

            # --- Layout: Vertical List (Compact) ---
            for cid in visible_children:
                child = tree["nodes"][cid]
                
                with st.container(border=True):
                    # Meta + Text
                    st.markdown(
                        f'''
                        <div class="suggestion-meta">
                            <span>🤖 {child.get("type", "Idea")}</span>
                            <span>{child.get("created_at", "")}</span>
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
                        st.markdown(f"<div style='font-size: 0.9em; color: #475569;'>{body_clean}</div>", unsafe_allow_html=True)
                        formatted_text_for_pin = f"**{title_clean}**\n\n{body_clean}"
                    else:
                        st.markdown(f"<div class='suggestion-text'>{raw_text}</div>", unsafe_allow_html=True)
                        formatted_text_for_pin = raw_text

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
                            
                            # Use FORMATED text for context
                            st.session_state.pinned_context.append({"id": cid, "text": formatted_text_for_pin})
                            
                            # --- Fix for Text Loss: Inherit Parent Content ---
                            # 1. Save the original "Idea" as the label for the Tree visualization
                            child.setdefault("metadata", {})["label"] = title_clean if is_structured else child["summary"][:30]
                            
                            # 2. Merge Parent Text ONLY (Do not touch editor with AI text)
                            parent_html = current_node.get("metadata", {}).get("html", "")
                            # If parent has no HTML but has summary, wrap it
                            if not parent_html and current_node["summary"]:
                                parent_html = f"<p>{current_node['summary']}</p>"
                                
                            # STRICT Inheritance: Editor stays exactly as it was
                            child["metadata"]["html"] = parent_html
                            child["summary"] = current_node["summary"]
                            
                            # -------------------------------------------------
                            
                            parent_id = current_node["id"]
                            sibling_ids = tree["nodes"][parent_id]["children"]
                            
                            for sib_id in sibling_ids:
                                if sib_id != cid and sib_id not in st.session_state.banned_ideas:
                                    st.session_state.banned_ideas.append(sib_id)

                            st.session_state.pop("current_critiques", None)
                            st.session_state.pop("last_refine_diff", None)
                            
                            # Navigate to the selected node to deepen the tree
                            navigate_to_node(tree, cid)
                            st.rerun()

                    # 📌 PIN
                    with c_pin:
                        if st.button("📌 Pin", key=f"p_{cid}", help="Keep this idea as context", use_container_width=True):
                            st.session_state.pinned_context.append({"id": cid, "text": formatted_text_for_pin})
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
            payload = st.session_state.pending_action

            try:
                response = handle_event(
                    st.session_state.tree,
                    UserEventType.ACTION,
                    {
                        "action": payload["action"],
                        "pinned_context": st.session_state.pinned_context,
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
                    # Save what we originally sent, so we can replace ONLY that part later
                    st.session_state["last_refine_original_target"] = payload["user_text"]
                    st.session_state.pop("refine_changes", None)

            except Exception as e:
                st.error(f"❌ Gemini Error: {e}")
                st.session_state.pending_action = None
                st.session_state.is_thinking = False
                st.stop()

            # DIVERGE → הילדים כבר נוספו לעץ ע"י controller

            st.session_state.pending_action = None
            st.session_state.is_thinking = False
            st.rerun()


if __name__ == "__main__":
    main()