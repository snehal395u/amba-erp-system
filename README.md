# Amba ERP — Prototype & FastAPI Backend

This repository contains a complete starter ERP project for Amba Enterprises Limited:
- Streamlit prototype: `streamlit_app.py` (Inventory + Order form that prints SQL)
- FastAPI backend: `app.py` with transactional order creation
- SQLAlchemy models: `models.py`
- Alembic migration example: `alembic/versions/0001_initial.py`
- Requirements and Dockerfile for easy deployment

## Quickstart (Streamlit prototype)
```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Quickstart (FastAPI)
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Notes:
- The FastAPI backend uses SQLite by default for local testing. Change `DATABASE_URL` in `models.py` to a PostgreSQL connection string for production.
- Alembic is included as an example migration; configure `alembic.ini` if you want to run migrations against PostgreSQL.
