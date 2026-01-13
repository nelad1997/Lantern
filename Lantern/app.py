import streamlit as st
from tree import init_tree, get_current_node, get_children

from definitions import UserEventType, ActionType
from controller import handle_event

# 1. Page Configuration
st.set_page_config(page_title="Lantern", layout="wide")


def main():
    st.title("Lantern: Tree of Thoughts Prototype")

    # 2. Initialize Session State (The Tree)
    # We store the tree in Streamlit's session_state so it persists between clicks.
    if "tree" not in st.session_state:
        # Initialize with a starting text
        initial_text = (
            "The integration of artificial intelligence (AI) into educational systems "
            "represents one of the most significant technological shifts in modern pedagogy."
        )
        st.session_state.tree = init_tree(initial_text)

    # Helper to access the tree easily
    tree = st.session_state.tree
    current_node = get_current_node(tree)

    # 3. Sidebar: Navigation / Tree View (Simplified)
    with st.sidebar:
        st.header("Navigation")
        st.info(f"Current Node ID:\n{current_node['id'][:8]}...")
        st.write(f"Status: **{current_node['status']}**")

        if st.button("Reset Tree"):
            del st.session_state.tree
            st.rerun()

    # 4. Main Area: Current Focus
    st.subheader("Current Focus")
    st.text_area(
        label="Reasoning / Draft",
        value=current_node["summary"],
        height=150,
        disabled=True  # Read-only for now, user selects actions below
    )

    # 5. Action Deck (The "Cards")
    st.divider()
    st.subheader("Agent Deck")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(" Diverge (Idea Expander)"):
            with st.spinner("Thinking..."):
                response = handle_event(
                    tree,
                    UserEventType.ACTION,
                    {"action": ActionType.DIVERGE}
                )
                st.rerun()  # Refresh to show new children

    with col2:
        if st.button(" Refine (Polisher)"):
            with st.spinner("Refining..."):
                response = handle_event(
                    tree,
                    UserEventType.ACTION,
                    {"action": ActionType.REFINE}
                )
                st.rerun()

    with col3:
        if st.button(" Critique (Devil's Advocate)"):
            with st.spinner("Critiquing..."):
                response = handle_event(
                    tree,
                    UserEventType.ACTION,
                    {"action": ActionType.CRITIQUE}
                )
                # Critique is a bit special, it might not create a node but show a message
                # For this prototype, we'll just handle it via the generic flow or
                # you can display the result in a popup/expander.
                if response.get("mode") == "critique":
                    st.warning(response.get("text"))

    # 6. Display Children (The Generated Options)
    children = get_children(tree)

    if children:
        st.divider()
        st.write(f"**Available Paths ({len(children)}):**")

        # Display each child as a selectable option
        for idx, child in enumerate(children):
            with st.container(border=True):
                st.markdown(f"**Option {idx + 1}**")
                st.write(child["summary"])

                # Button to choose this path
                if st.button(f"Select Option {idx + 1}", key=child["id"]):
                    handle_event(
                        tree,
                        UserEventType.CHOOSE_OPTION,
                        {"option_index": idx}
                    )
                    st.rerun()


if __name__ == "__main__":
    main()