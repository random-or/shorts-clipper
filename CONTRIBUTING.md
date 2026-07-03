# Contributing to Shorts Clipper

First off, thank you for considering contributing to Shorts Clipper! It's people like you that make this tool incredible.

## 🧠 Architectural Philosophy

Before writing code, please understand the core tenets of Shorts Clipper:

1. **Local-First & Deterministic:** We believe that core logic (like selecting a good video clip) should be mathematically sound, deterministic, and run locally. LLMs (like Gemini) are used only for semantic understanding (e.g., SEO metadata or verifying context), NOT as the core processing engine.
2. **Zero Regression:** Every PR must pass all existing tests. If you add a new feature, add a test. We maintain 100% reliability on the core pipeline.
3. **Decoupled Architecture:** The system is split into independent domains (Scout, Editorial Engine, Rendering, Publishing). If you modify the Scout, it should not break Rendering. 
4. **Resilience & Fallbacks:** Always handle network failures, quota exhaustion, and API timeouts gracefully.

## 🛠 Setup for Development

1. **Clone the repo:**
   ```bash
   git clone https://github.com/your-org/shorts-clipper.git
   cd shorts-clipper
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install Pre-commit Hooks (Optional but recommended):**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## 🧪 Testing

We use `pytest` for all unit and integration testing.

Run the test suite:
```bash
pytest tests/
```

Ensure you have a 100% pass rate before submitting a pull request.

## 🚀 Submitting a Pull Request

1. Fork the repository and create your branch from `main`.
2. Write clean, heavily-documented code. We love type hints (`typing`) and docstrings.
3. Ensure the test suite passes.
4. Update any relevant documentation (README, Architecture docs).
5. Submit your PR with a clear, detailed description of the problem solved and the implementation details.

Welcome to the team!
