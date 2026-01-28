# Lantern - Changelog / Recent Updates

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
