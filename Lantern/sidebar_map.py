import streamlit as st
from tree import get_node, navigate_to_node


def render_sidebar_map(tree):
    """
    Renders the vertical 'Reasoning Map' in the sidebar.
    """

    # 1. CSS Injection for the Subway Map Look
    st.markdown("""
    <style>
        /* Container for the timeline */
        .timeline-container {
            position: relative;
            padding-left: 20px;
            margin-bottom: 20px;
            border-left: 2px solid #e2e8f0; /* The main vertical line */
        }

        /* The Node Dots */
        .timeline-dot {
            position: absolute;
            left: -27px; /* Align with the line */
            top: 15px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: white;
            border: 2px solid #cbd5e1;
            z-index: 10;
        }

        .timeline-dot.active {
            background-color: #7c3aed; /* Purple-600 */
            border-color: #7c3aed;
            box-shadow: 0 0 0 4px #ede9fe; /* Ring effect */
        }

        .timeline-dot.pruned {
            width: 8px;
            height: 8px;
            left: -25px;
            border: 2px solid #94a3b8;
            background-color: #f1f5f9;
        }

        /* Styling Streamlit Buttons to look like cards */
        div[data-testid="stVerticalBlock"] button {
            text-align: left;
            border: none;
            background-color: transparent;
            padding: 4px 0px;
            transition: all 0.2s;
            color: #64748b;
        }

        div[data-testid="stVerticalBlock"] button:hover {
            color: #7c3aed;
            padding-left: 4px;
        }

        div[data-testid="stVerticalBlock"] button p {
            font-size: 0.9rem;
            font-weight: 400;
        }

        /* Active Node Styling */
        .active-node-box {
            background-color: #f5f3ff; /* Purple-50 */
            border: 1px solid #ddd6fe;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 12px;
        }

        .active-title {
            color: #5b21b6;
            font-weight: 700;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }

        .active-summary {
            color: #1e293b;
            font-size: 0.95rem;
            line-height: 1.4;
        }

    </style>
    """, unsafe_allow_html=True)

    # 2. Logic: Trace path from Root to Current
    current_id = tree["current"]
    path = []
    temp_id = current_id

    # Backtrack from current to root to find the active path
    while temp_id:
        node = get_node(tree, temp_id)
        path.append(node)
        temp_id = node["parent"]

    path.reverse()  # Now it's [Root, ..., Current]

    st.sidebar.markdown("### 🗺️ Reasoning Map")

    # 3. Render the Path
    with st.sidebar.container():
        st.markdown('<div class="timeline-container">', unsafe_allow_html=True)

        for i, node in enumerate(path):
            is_current = (node["id"] == current_id)

            # --- Render The Active Node ---

            # 1. The Dot (Visual only)
            st.markdown(f"""
            <div class="timeline-dot active" style="top: {i * 100}px;"></div>
            """, unsafe_allow_html=True)

            # 2. The Content
            if is_current:
                # Highlighted Box for Current Node
                st.markdown(f"""
                <div class="active-node-box">
                    <div class="active-title">Currently Editing</div>
                    <div class="active-summary">{node['summary'][:60]}...</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Clickable Button for Ancestors (to navigate back)
                # Note: We limit summary length to prevent button overflow
                if st.button(f"{node['summary'][:40]}...", key=f"nav_{node['id']}"):
                    navigate_to_node(tree, node['id'])
                    st.rerun()

            # --- Render Siblings (Pruned/Alternatives) ---
            if node["parent"]:
                parent = get_node(tree, node["parent"])
                siblings = parent["children"]

                for sib_id in siblings:
                    if sib_id == node["id"]:
                        continue  # Skip self

                    if sib_id in st.session_state.banned_ideas:
                        continue  # Skip banned

                    sib_node = get_node(tree, sib_id)

                    # Render Ghost Node (Pruned branch)
                    col_ghost, col_btn = st.columns([0.1, 0.9])
                    with col_btn:
                        if st.button(f"⚪ {sib_node['summary'][:30]}", key=f"ghost_{sib_id}",
                                     help="Restore this alternative path"):
                            navigate_to_node(tree, sib_id)
                            st.rerun()

            # Add spacing between nodes
            st.markdown("<div style='margin-bottom: 24px'></div>", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # Close timeline-container

    # 4. "Next" Indicator
    st.sidebar.markdown("""
    <div style="margin-left: 26px; color: #94a3b8; font-size: 0.8rem; font-style: italic;">
       ↓ Awaiting next thought...
    </div>
    """, unsafe_allow_html=True)