# streamlit_app.py - Professional ERP Prototype
import streamlit as st
import pandas as pd
import datetime
import os
import uuid

def sql_escape(val):
    if val is None: return "NULL"
    if isinstance(val, (int, float)): return str(val)
    if isinstance(val, datetime.date): return f"'{val.isoformat()}'"
    s = str(val).replace("'", "''")
    return f"'{s}'"

st.set_page_config(page_title="ERP Prototype", layout="wide")

st.markdown("<h1 style='text-align:center;color:#4F81BD;'> ERP Prototype — Inventory & Orders</h1>", unsafe_allow_html=True)
st.markdown("---")

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
    ])

df_products['id'] = df_products['id'].astype(int)
df_products['current_stock'] = df_products['current_stock'].astype(int)
df_products['price'] = df_products['price'].astype(float)

col1, col2 = st.columns([2, 3])

# Inventory Display
with col1:
    st.markdown("### Inventory")
    st.dataframe(df_products)

# Order Form
with col2:
    st.markdown("### Create New Sales Order")
    sample_customers = [
        {"id": 1, "name": "Amba Distributors"},
        {"id": 2, "name": "TransCo Pvt Ltd"},
    ]
    cust_options = {c['name']: c['id'] for c in sample_customers}

    with st.form("order_form", clear_on_submit=False):
        order_number = st.text_input("Order Number", value=f"ORD-{datetime.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}")
        customer_name = st.selectbox("Customer", options=list(cust_options.keys()))
        order_date = st.date_input("Order Date", value=datetime.date.today())
        created_by = st.text_input("Created by", value="operator")
        num_lines = st.number_input("Number of lines", min_value=1, max_value=5, value=1)

        lines = []
        for i in range(int(num_lines)):
            st.markdown(f"**Line {i+1}**")
            col_a, col_b = st.columns([2, 2])
            with col_a:
                product_choice = st.selectbox(f"Product (line {i+1})", options=df_products['name'].tolist(), key=f"prod_{i}")
                qty = st.number_input(f"Qty (line {i+1})", min_value=1, value=1, key=f"qty_{i}")
            with col_b:
                st.write("Enter up to 3 prices for same qty:")
                prices = [
                    st.number_input(f"Price 1 (line {i+1})", min_value=0.0, value=float(df_products.loc[df_products['name']==product_choice,'price'].iloc[0]), key=f"price1_{i}"),
                    st.number_input(f"Price 2 (line {i+1})", min_value=0.0, value=0.0, key=f"price2_{i}"),
                    st.number_input(f"Price 3 (line {i+1})", min_value=0.0, value=0.0, key=f"price3_{i}")
                ]

            prod_row = df_products[df_products['name'] == product_choice].iloc[0]
            for price in [p for p in prices if p > 0]:
                lines.append({
                    "product_id": int(prod_row['id']),
                    "product_name": product_choice,
                    "qty": int(qty),
                    "unit_price": float(price)
                })

        submitted = st.form_submit_button("Validate & Generate")

    if submitted:
        total_amount = sum([li['qty'] * li['unit_price'] for li in lines])
        st.success(f"Validation passed — total = ₹{total_amount:.2f}")
        st.markdown("### Generated SQL")
        st.code(f"INSERT INTO orders (order_number, customer_id, order_date, total_amount, status, created_by) VALUES ({sql_escape(order_number)}, {cust_options[customer_name]}, {sql_escape(order_date)}, {total_amount}, 'confirmed', {sql_escape(created_by)});")
        
        for li in lines:
            line_total = li['qty'] * li['unit_price']
            sql_line = f"INSERT INTO order_items (order_id, product_id, qty, unit_price, line_total) VALUES ((SELECT id FROM orders WHERE order_number={sql_escape(order_number)}), {sql_escape(li['product_id'])}, {sql_escape(li['qty'])}, {sql_escape(li['unit_price'])}, {sql_escape(line_total)});"
            st.code(sql_line)
