# streamlit_app.py - Professional ERP Prototype (Polished UI + correct price/qty logic)
import streamlit as st
import pandas as pd
import datetime
import os
import uuid
from decimal import Decimal, ROUND_HALF_UP

# --- helpers ---------------------------------------------------------------
def sql_escape(val):
    if val is None: return "NULL"
    if isinstance(val, (int, float, Decimal)): return str(val)
    if isinstance(val, datetime.date): return f"'{val.isoformat()}'"
    s = str(val).replace("'", "''")
    return f"'{s}'"

def format_currency(v):
    return f"₹{float(Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)):.2f}"

# page setup
st.set_page_config(page_title="ERP Prototype", layout="wide")
st.markdown(
    """
    <style>
      .header {text-align:center; color:#ffffff; background: linear-gradient(90deg,#1F4E79,#4F81BD); padding: 14px; border-radius: 8px;}
      .card {background: #ffffff; padding: 12px; border-radius:10px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);}
      .muted {color:#6b7280; font-size:0.95rem;}
    </style>
    """, unsafe_allow_html=True
)
st.markdown("<div class='header'><h1 style='margin:0'>Amba ERP — Inventory & Orders</h1></div>", unsafe_allow_html=True)
st.markdown("")

# --- data load -------------------------------------------------------------
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

# normalize types
df_products['id'] = df_products['id'].astype(int)
df_products['current_stock'] = df_products['current_stock'].astype(int)
df_products['price'] = df_products['price'].astype(float)

# sample customers
sample_customers = [
    {"id": 1, "name": "Amba Distributors"},
    {"id": 2, "name": "TransCo Pvt Ltd"},
]
cust_options = {c['name']: c['id'] for c in sample_customers}

# --- layout ---------------------------------------------------------------
col_left, col_right = st.columns([2, 3])

with col_left:
    st.markdown("### Inventory Snapshot")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.dataframe(df_products[['id','sku','name','current_stock','reorder_level','price']].rename(columns={
        'current_stock':'Stock','reorder_level':'Reorder','price':'Default Price'
    }), height=320)
    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    st.markdown("### Create New Sales Order")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    with st.form("order_form", clear_on_submit=False):
        order_number = st.text_input("Order Number", value=f"ORD-{datetime.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}")
        customer_name = st.selectbox("Customer", options=list(cust_options.keys()))
        order_date = st.date_input("Order Date", value=datetime.date.today())
        created_by = st.text_input("Created by", value="operator")
        num_lines = st.number_input("Number of lines", min_value=1, max_value=5, value=1)

        # allow up to 3 file attachments (e.g., PO, attachments)
        st.markdown("**Attachments (up to 3 files)**")
        uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True)
        if uploaded_files and len(uploaded_files) > 3:
            st.warning("Maximum 3 files allowed — extra files will be ignored.")
            uploaded_files = uploaded_files[:3]

        # build order lines
        lines_display = []
        lines_for_insert = []
        error_msgs = []
        for i in range(int(num_lines)):
            st.markdown(f"**Line {i+1}**")
            a, b = st.columns([2, 2])
            with a:
                product_choice = st.selectbox(f"Product (line {i+1})", options=df_products['name'].tolist(), key=f"prod_{i}")
                qty = st.number_input(f"Qty (line {i+1})", min_value=1, value=1, key=f"qty_{i}")
            with b:
                st.markdown("Enter up to 3 prices (each price will create a separate line with same qty if > 0)")
                default_price = float(df_products.loc[df_products['name'] == product_choice, 'price'].iloc[0])
                p1 = st.number_input(f"Price 1 (line {i+1})", min_value=0.0, value=float(default_price), format="%.2f", key=f"price1_{i}")
                p2 = st.number_input(f"Price 2 (line {i+1})", min_value=0.0, value=0.0, format="%.2f", key=f"price2_{i}")
                p3 = st.number_input(f"Price 3 (line {i+1})", min_value=0.0, value=0.0, format="%.2f", key=f"price3_{i}")

            # product row for validation
            prod_row = df_products[df_products['name'] == product_choice].iloc[0]
            if qty > int(prod_row['current_stock']):
                error_msgs.append(f"Line {i+1}: requested qty {qty} exceeds stock ({prod_row['current_stock']}) for {product_choice}")

            # capture each non-zero price as separate order line (same qty)
            for price in [p for p in (p1, p2, p3) if p and p > 0]:
                line = {
                    "product_id": int(prod_row['id']),
                    "product_name": product_choice,
                    "qty": int(qty),
                    "unit_price": float(price),
                    "line_total": float(int(qty) * float(price))
                }
                lines_for_insert.append(line)
                lines_display.append(line)

        submitted = st.form_submit_button("Validate & Generate SQL")

    # show validation results
    if submitted:
        if error_msgs:
            for e in error_msgs:
                st.error(e)
            st.warning("Fix the errors above and resubmit.")
        elif len(lines_for_insert) == 0:
            st.warning("No valid price lines found. Please enter at least one price > 0.")
        else:
            total_amount = sum([l['line_total'] for l in lines_for_insert])
            st.success(f"Validation passed — total = {format_currency(total_amount)}")
            st.markdown("#### Summary")
            st.table(pd.DataFrame(lines_for_insert)[['product_name','qty','unit_price','line_total']].rename(columns={
                'product_name':'Product','qty':'Qty','unit_price':'Unit Price','line_total':'Line Total'
            }))
            # SQL generation (INSERT statements)
            st.markdown("### Generated SQL (for review / paste into DB)")
            order_insert = f"INSERT INTO orders (order_number, customer_id, order_date, total_amount, status, created_by) VALUES ({sql_escape(order_number)}, {cust_options[customer_name]}, {sql_escape(order_date)}, {total_amount}, 'confirmed', {sql_escape(created_by)});"
            st.code(order_insert)
            # Order items and inventory log SQL
            for li in lines_for_insert:
                line_total = li['line_total']
                sql_line = (
                    f"INSERT INTO order_items (order_id, product_id, qty, unit_price, line_total) "
                    f"VALUES ((SELECT id FROM orders WHERE order_number={sql_escape(order_number)}), "
                    f"{sql_escape(li['product_id'])}, {sql_escape(li['qty'])}, {sql_escape(li['unit_price'])}, {sql_escape(line_total)});"
                )
                st.code(sql_line)
                # inventory update + log
                st.code(
                    f"-- Inventory update for product_id={li['product_id']}\n"
                    f"UPDATE products SET current_stock = current_stock - {li['qty']} WHERE id = {li['product_id']};\n"
                    f"INSERT INTO inventory_log (product_id, change_qty, reason, prev_stock, new_stock) VALUES ({li['product_id']}, {-li['qty']}, 'Sale {order_number}', (SELECT current_stock FROM products WHERE id={li['product_id']}) + {li['qty']}, (SELECT current_stock FROM products WHERE id={li['product_id']}) );"
                )
            if uploaded_files:
                st.info(f"{len(uploaded_files)} file(s) attached (not stored): " + ", ".join([f.name for f in uploaded_files]))

    st.markdown("</div>", unsafe_allow_html=True)

# --- small footer ---------------------------------------------------------
st.markdown("---")
st.markdown("<div class='muted'>Tip: Use the API (app.py) for programmatic order creation. This Streamlit app is a front-end prototype that generates SQL for your review.</div>", unsafe_allow_html=True)
