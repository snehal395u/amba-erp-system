ERP Prototype — Inventory & Orders

A lightweight ERP (Enterprise Resource Planning) prototype built with Streamlit, FastAPI, and SQLAlchemy.
This system is designed for small-to-medium manufacturers to manage products, inventory, customers, and sales orders efficiently.

* Features *

User Authentication

Secure login system for operators and admins.

Inventory Management

View and update product stock levels.

Track reorder points and pricing.

Sales Order Workflow

Create sales orders with multiple lines.

Support for up to 3 prices per product line (same quantity).

Automatic calculation of totals.

SQL queries generated for database persistence.

Database Models (SQLAlchemy)

Users, Customers, Products, Orders, OrderItems, and InventoryLog.

SQLite by default, easy to switch to PostgreSQL/MySQL.

REST APIs (FastAPI)

Endpoints for authentication, product listing, order creation.

JSON responses for integration with other systems.

Streamlit Frontend

Clean, professional UI with two sections:

1. Inventory Overview

2. New Sales Order Form

 Project Structure
erp-prototype/
│── app.py              # FastAPI app (authentication + order APIs)
│── models.py           # SQLAlchemy models & database schema
│── streamlit_app.py    # Streamlit frontend for ERP prototype
│── management_report.xlsx  # Optional sample Excel data
│── requirements.txt    # Dependencies
│── README.md           # Project documentation

 Installation

Clone the repository

git clone https://github.com/your-username/erp-prototype.git
cd erp-prototype


Create virtual environment & install dependencies

python -m venv venv
source venv/bin/activate   # (Linux/Mac)
venv\Scripts\activate      # (Windows)
pip install -r requirements.txt


Initialize database

python models.py


Run backend (FastAPI)

uvicorn app:app --reload


API will be available at: http://localhost:8000

Run frontend (Streamlit)

streamlit run streamlit_app.py

4 Example API Endpoints

POST /login → Authenticate user

GET /products → List products

POST /orders → Create sales order

GET /orders/{id} → Fetch order details

5 Tech Stack

Frontend: Streamlit

Backend: FastAPI

Database: SQLite (default) / PostgreSQL / MySQL

ORM: SQLAlchemy

Language: Python 3.10+

6 Future Enhancements

Purchase order workflow

Role-based access (Admin / Operator)

Reporting dashboard with KPIs

Email / PDF invoice generation

📜 License

This project is licensed under the MIT License.
You are free to use, modify, and distribute with attribution.
