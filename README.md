# Logistic text-to-sql

## Project Setup and Execution Guide

This project is optimised for reproducibility using the `uv` package manager, but also supports standard Python virtual environments using `pip`.

For maximum compatibility, use python 3.13.5>=

**The projects main entrypoint is notebooks/submission.ipynb**

---

### Option 1: Using `uv` (Recommended)

If you have `uv` installed, this is the most efficient method to ensure environment parity.

1. Unzip the project folder.
2. Open a terminal in the project root directory.
3. Launch the notebook server using the following commands:
```bash
uv venv
uv pip install -r requirements.txt
uv run jupyter lab
```

---

### Option 2: Standard Python (Alternative)

If you do not have `uv` installed, follow these steps to set up the environment manually:

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. Install the necessary dependencies:
```bash
pip install -r requirements.txt
```

3. Launch the Jupyter server:
```bash
jupyter lab
```

---

### Configuration

Before executing the cells in the notebook, ensure you have a `.env` file located in the project root directory containing your API credentials:
e.g.
```env
OPENAI_API_KEY=your_actual_key_here
```
there's a script inside notebooks/submission.ipynb that you can edit to set easily

---

### Project Structure
```
.
├── notebooks/       # Contains the main submission notebook (submission.ipynb)
├── src/             # Core logic, pipeline components, and configuration files
├── data/            # Directory for raw and processed dataset storage
└── requirements.txt # List of project dependencies
```
