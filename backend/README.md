# NetMon Backend

FastAPI + SQLAlchemy backend for the NetMon network monitoring dashboard.
See the repository root `README.md` for full project architecture and
rationale.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
pytest
```
