# Lantern 🏮 - AI-Augmented Thinking & Writing

**Lantern** is an advanced AI-powered writing partner designed for researchers, students, and professional writers. Unlike standard LLM chat interfaces, Lantern is built around the concept of a **"Thought Tree"**—a visual, branching map of your reasoning process.

The system doesn't just "fix" your text; it acts as a **Senior Research Partner** that diagnoses logical risks, suggests divergent perspectives, and enforces academic rigor.

---

## 🏗️ What is Lantern?

Lantern transforms writing from a linear task into a multi-dimensional exploration. It helps you:
- **🌱 Explore **: Don't settle for the first draft. Use the "Expand" tool to see different ways a paragraph could be developed.
- **🛡️ Stress-Test Logic**: The "Critique" engine uses a specialized "Devil's Advocate" mode to find gaps in your evidence.
- **🪄 Refine with Purpose**: Automate the "Old-to-New" information principle for professional, cohesive prose.
- **🗺️ Visualize Your Mind**: Every interaction is mapped on a Graphviz tree in the sidebar, allowing you to "time-travel" between different versions of your work.

---

## 🚀 Installation & Setup

These instructions will get you running Lantern on your local machine.

### 1. Prerequisites
- **Python 3.10+**
- **Graphviz**: Required for rendering the Thought Tree.
  - **Windows**: Install via [graphviz.org](https://graphviz.org/download/). Ensure the `bin` folder is added to your System PATH or installed in `C:\Program Files\Graphviz`.
  - **Mac**: `brew install graphviz`
  - **Linux**: `sudo apt-get install graphviz`

### 2. Get the Code
Clone the repository and navigate to the project folder:
```bash
git clone https://github.com/nelad1997/Lantern.git
cd Lantern/Lantern
```
*(Note: The application core is located in the `Lantern/` subdirectory).*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration
Open `.env` and paste your API Key:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```
   *You can get a free API key at [Google AI Studio](https://aistudio.google.com/).*

### 4.1 Model Settings
Lantern was developed, tested, and evaluated using Gemini 2.5 Pro — this is the recommended default model.
change the AI model (e.g., if you have access to different versions-Gemini 2.5 Pro is the deafult version):
1. Open `llm_client.py`.
2. Go to **Line 69** (look for `model_name="..."`).
3. Change the string to your desired model (e.g.,`"gemini-2.5-flash"`).


### 5. Run the App
```bash
streamlit run app.py
```

---

## 📂 Repository Map

### 🏗️ Core Application
- **`app.py`**: Main entry point and UI orchestration.
- **`sidebar_map.py`**: Thought Tree rendering and navigation.
- **`controller.py`**: State management and action handler.
- **`tree.py`**: Hierarchical data structure and sync logic.

### 🧠 Logic & AI Engine
- **`llm_client.py`**: Gemini API integration.
- **`prompt_builder.py`**: System prompt engineering.
- **`academic_writing_principles`**: Ruleset for scholarly standards.
- **`definitions.py`**: Project Enums and constants.

### ⚙️ Environment & Deployment
- **`requirements.txt`**: Python libraries.
- **`packages.txt`**: Binary dependencies for Streamlit Cloud.
- **`runtime.txt`**: Python environment version.

---

## ☁️ Cloud Deployment
Lantern is running live at: **[https://lantern.streamlit.app/](https://lantern.streamlit.app/)**


---
*Created for the Intelligent Interactive Systems course at Technion.*
