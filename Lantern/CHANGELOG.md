# Lantern - Changelog / Recent Updates

## [2026-01-29] - UI Overhaul & Structural Stability

### ✨ New Features
- **AI Context & Structure Tabbed UI**: Consolidated Focus Range, Segmentation, and Focus Preview into a single, clean tabbed interface under the "🧠 AI Context & Structure" section.
- **Dedicated Help Tooltips**: Added granular "i" icons for each internal tab, providing specific guidance on document focus and structural mapping.
- **Differentiated Reset Logic**:
    - **Sidebar Reset (🗑)**: Now resets the AI Thought Tree and reasoning context while preserving the current editor draft.
    - **Full System Reset (🗑)**: Located above the editor, this performs a complete workspace wipe (text, tree, and meta-data) for a total fresh start.

### 🛠️ Bug Fixes & Reliability
- **Paragraph Selection Persistence**: Fixed a critical bug where the paragraph list would disappear during AI analysis. Standardized all focus mode strings to ensure 100% targeting accuracy.
- **Execution Logic Synchronization**: Resolved a case-sensitivity mismatch between the UI and the controller that caused AI actions to default to the first paragraph regardless of user selection.
- **Robust State Initialization**: Re-engineered the application loop to ensure document segments are always available for AI actions, even after reruns or tab switches.
- **Critique Prompt Fix**: Fixed a dictionary key reference error in the Refine/Critique logic.

### 🧠 Performance & UX
- **Modern Tabbed Layout**: Reduced vertical scrolling by organizing metadata tools into horizontal tabs, creating a more intuitive and dashboard-like user experience.
- **Hebrew/English Symmetry**: Standardized all internal logic strings to ensure multi-lingual inputs are processed with consistent focus rules.

---

## [2026-01-28] - Stability & Performance Update

### ✨ New Features
- **Focus Mode Improvements**: Added a direct shortcut button to switch back from "Specific Paragraph" to "Whole Document" mode for smoother navigation.
- **Manual AI Map Refresh**: Users can now manually trigger a logical structure scan with the `🔄 Refresh Logical Map` button.
- **Improved Tooltips**: Expanded information (i) icon in Focus Mode with detailed usage instructions for all analysis tools.

### 🛠️ Bug Fixes & Reliability
- **Robust LLM Client**: Re-engineered the Gemini API connector with automatic retries and exponential backoff to handle Rate Limits (TPM/429 errors) much better.
- **State Clear Fix**: Clearing the editor via the trash icon now also correctly resets the Logical Structure (AI Map) view.
- **Execution Reliability**: Moved the AI processing logic to the top level of the application to ensure Expand, Critique, and Refine buttons respond instantly regardless of the current UI state.
- **Fixed Navigation Glitch**: Resolved an issue where navigating the tree map during active analysis could lead to "undefined" context labels.

### 🧠 Performance Optimization
- **Token Protection**: Reduced unnecessary AI calls by disabling continuous auto-scanning. The system now only scans structural changes when specifically requested or after a major AI reasoning action.
- **TPM Management**: Added a mandatory cooldown between API calls to prevent hitting project-level quotas.
