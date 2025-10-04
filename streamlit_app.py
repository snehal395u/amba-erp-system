# streamlit_app.py
import streamlit as st
import pandas as pd
import datetime
import os
import uuid

def sql_escape(val):
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, datetime.date):
        return f"'{val.isoformat()}'"
    s = str(val).replace("'", "''")
    return f"'{s}'"

st.set_page_config(page_title="ERP Prototype - Inventory & Order Form", layout="wide")
st.title("ERP Prototype — Inventory List & Order Form")

EXCEL_PATH = "management_report.xlsx"
if os.path.exists(EXCEL_PATH):
    try:
        df_products = pd.read_excel(EXCEL_PATH, sheet_name="Products")
    except Exception:
        df_products = None
else:
    df_products = None

if df_products is None:
    df_products = pd.DataFrame([
        {"id": 1, "sku": "LAM-001", "name": "Lamination A", "uom": "pcs", "current_stock": 120, "reorder_level": 20, "price": 50.0},
        {"id": 2, "sku": "LAM-002", "name": "Lamination B", "uom": "pcs", "current_stock": 45,  "reorder_level": 10, "price": 75.0},
        {"id": 3, "sku": "STAMP-01", "name": "Motor Stamp 1", "uom": "pcs", "current_stock": 300, "reorder_level": 50, "price": 12.5},
        {"id": 4, "sku": "STAMP-02", "name": "Motor Stamp 2", "uom": "pcs", "current_stock": 5,   "reorder_level": 10, "price": 20.0},
    ])

df_products['id'] = df_products['id'].astype(int)
df_products['current_stock'] = df_products['current_stock'].astype(int)
df_products['price'] = df_products['price'].astype(float)

col1, col2 = st.columns([2, 3])
with col1:
    st.header("Inventory")
    st.markdown("Inventory loaded from `management_report.xlsx` if present, otherwise sample data.")
    st.dataframe(df_products.style.format({"price": "{:.2f}"}), height=400)
    st.markdown(f"Total SKUs: **{len(df_products)}**")

with col2:
    st.header("Create New Sales Order")
    sample_customers = [
        {"id": 1, "name": "Amba Distributors"},
        {"id": 2, "name": "TransCo Pvt Ltd"},
        {"id": 3, "name": "Electric Supplies Inc"}
    ]
    cust_options = {c['name']: c['id'] for c in sample_customers}

    with st.form("order_form", clear_on_submit=False):
        order_number = st.text_input("Order Number (e.g. ORD-2025-0001)", value=f"ORD-{datetime.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}")
        customer_name = st.selectbox("Customer", options=list(cust_options.keys()))
        order_date = st.date_input("Order Date", value=datetime.date.today())
        created_by = st.text_input("Created by", value="operator")
        num_lines = st.number_input("Number of lines", min_value=1, max_value=10, value=1)

        lines = []
        st.markdown("### Order lines")
        for i in range(int(num_lines)):
            st.markdown(f"**Line {i+1}**")
            col_a, col_b, col_c = st.columns([3, 1, 1])
            with col_a:
                product_choice = st.selectbox(f"Product (line {i+1})", options=df_products['name'].tolist(), key=f"prod_{i}")
            with col_b:
                qty = st.number_input(f"Qty (line {i+1})", min_value=1, value=1, key=f"qty_{i}")
            with col_c:
                price = float(df_products.loc[df_products['name'] == product_choice, 'price'].iloc[0])
                st.markdown(f"Unit price: **{price:.2f}**")
            prod_row = df_products[df_products['name'] == product_choice].iloc[0]
            lines.append({
                "product_id": int(prod_row['id']),
                "product_name": product_choice,
                "qty": int(qty),
                "unit_price": float(price)
            })

        submitted = st.form_submit_button("Validate & Generate SQL INSERT")

    if submitted:
        errors = []
        if not order_number.strip():
            errors.append("Order number is required.")
        if customer_name not in cust_options:
            errors.append("Customer invalid.")
        if len(lines) == 0:
            errors.append("At least one order line required.")
        for li in lines:
            prod = df_products[df_products['id'] == li['product_id']].iloc[0]
            if li['qty'] <= 0:
                errors.append(f"Qty must be >0 for product {li['product_name']}.")
        if errors:
            st.error("Validation errors:\n- " + "\n- ".join(errors))
        else:
            total_amount = sum([li['qty'] * li['unit_price'] for li in lines])
            order_values = {
                "order_number": order_number,
                "customer_id": cust_options[customer_name],
                "order_date": order_date,
                "total_amount": total_amount,
                "status": "confirmed",
                "created_by": created_by
            }

            cols = ["order_number", "customer_id", "order_date", "total_amount", "status", "created_by"]
            cols_sql = ", ".join(cols)
            vals_sql = ", ".join([sql_escape(order_values[c]) for c in cols])
            insert_order_sql = f"INSERT INTO orders ({cols_sql}) VALUES ({vals_sql});"
            st.markdown("### Generated SQL")
            st.code(insert_order_sql)

            st.markdown("#### Order lines (inserts for order_items)")
            for li in lines:
                li_cols = ["order_id", "product_id", "qty", "unit_price", "line_total"]
                line_total = li['qty'] * li['unit_price']
                li_vals = [
                    "(SELECT id FROM orders WHERE order_number = " + sql_escape(order_number) + " LIMIT 1)",
                    sql_escape(li['product_id']),
                    sql_escape(li['qty']),
                    sql_escape(li['unit_price']),
                    sql_escape(line_total)
                ]
                sql_line = f"INSERT INTO order_items ({', '.join(li_cols)}) VALUES ({', '.join(li_vals)});"
                st.code(sql_line)

            st.success(f"Validation passed — total = {total_amount:.2f}. SQL statements generated above.")
            st.info("Note: In a real DB transaction, you'd INSERT the orders row, get its id, then INSERT order_items, and update the products table and inventory_log.")

st.markdown("---")
st.markdown("**Developer notes:** This prototype prints SQL insert statements only (no DB connection). For a production backend, implement an API endpoint that performs the transactional logic described in the architecture doc.")
