# Lantern 🏮 - AI-Augmented Thinking & Writing

<p align="center">
  <img src="logo.jpg" alt="Lantern Logo" width="200"/>
</p>

**Lantern** is an advanced AI-powered writing partner designed for researchers, students, and professional writers. Unlike standard LLM chat interfaces, Lantern is built around the concept of a **"Thought Tree"**—a visual, branching map of your reasoning process.

The system doesn't just "fix" your text; it acts as a **Senior Research Partner** that diagnoses logical risks, suggests divergent perspectives, and enforces academic rigor in real-time.

---

## 🏗️ What is Lantern?

Lantern transforms writing from a linear task into a multi-dimensional exploration. It helps you:
- **🌱 Expand & Explore**: Don't settle for the first draft. Use the "Expand" tool to see different ways a reasoning node could be developed.
- **🛡️ Stress-Test Logic**: The "Critique" engine uses a specialized "Devil's Advocate" mode to find gaps in your evidence and logical fallacies.
- **✨ Refine with Purpose**: Automate the "Old-to-New" information principle for professional, cohesive prose.
- **🗺️ Visualize Your Mind**: Every interaction is mapped on a Graphviz-powered **Node** tree in the sidebar, allowing you to "time-travel" between different versions of your work.
- **🎯 Precise AI Focus**: Choose between analyzing the **Whole Document** or a **Specific Paragraph** for granular improvements.

---

## 🚀 Installation & Setup

These instructions will get you running Lantern on your local machine.

### 1. Prerequisites
- **Python 3.10+**
- **Graphviz**: Required for rendering the Thought Tree.
  - **Windows**: Install via [graphviz.org](https://graphviz.org/download/). Ensure the `bin` folder is added to your System PATH (e.g., `C:\Program Files\Graphviz\bin`).
  - **Mac**: `brew install graphviz`
  - **Linux**: `sudo apt-get install graphviz`

### 2. Get the Code
Clone the repository and navigate to the project folder:
```bash
git clone https://github.com/nelad1997/Lantern.git
cd Lantern/Lantern
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file in the `Lantern/` folder and paste your Gemini API Key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```
*You can get a free API key at [Google AI Studio](https://aistudio.google.com/).*

### 5. Run the App
```bash
streamlit run app.py
```

---

## 📂 Repository Map

### 🏗️ Core Application
- **`app.py`**: Main entry point, UI orchestration, and real-time synchronization logic.
- **`sidebar_map.py`**: Node-based navigation and SVG rendering.
- **`controller.py`**: State management, AI action handling, and fuzzy replacements.
- **`tree.py`**: Hierarchical data structure, state persistence, and session management.

### 🧠 Logic & AI Engine
- **`llm_client.py`**: Gemini 2.5 Pro API integration and rate limiting.
- **`prompt_builder.py`**: Advanced system prompt engineering.
- **`academic_writing_principles`**: Internal knowledge base for scholarly standards.
- **`definitions.py`**: Core Enums and shared global constants.

### ⚙️ Environment & Deployment
- **`requirements.txt`**: Complete Python dependency list.
- **`packages.txt`**: System-level dependencies for Streamlit Cloud.
- **`runtime.txt`**: Python runtime specifications.

---

## ☁️ Cloud Deployment
Lantern is running live at: **[https://lantern.streamlit.app/](https://lantern.streamlit.app/)**

---
*Created for the Intelligent Interactive Systems course at Technion.*
