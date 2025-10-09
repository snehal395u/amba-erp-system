# streamlit_app.py - Professional ERP Prototype (updated)
import streamlit as st
import pandas as pd
import datetime
import os
import uuid
from decimal import Decimal, ROUND_HALF_UP

# Import your existing models (no change to models.py expected)
from models import SessionLocal, Product, Customer, Order, OrderItem, InventoryLog

# --- Helpers ---
def sql_escape(val):
    if val is None: return "NULL"
    if isinstance(val, (int, float, Decimal)): return str(val)
    if isinstance(val, datetime.date): return f"'{val.isoformat()}'"
    s = str(val).replace("'", "''")
    return f"'{s}'"

def money(v):
    # Round to 2 decimals
    if v is None:
        return "₹0.00"
    q = Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"₹{q}"

def get_products_from_db():
    session = SessionLocal()
    try:
        prods = session.query(Product).order_by(Product.id).all()
        return prods
    finally:
        session.close()

def get_customers_from_db():
    session = SessionLocal()
    try:
        custs = session.query(Customer).order_by(Customer.id).all()
        return custs
    finally:
        session.close()

def create_order_in_db(order_number, customer_id, order_date, created_by, lines, total_amount):
    """
    lines: list of dicts: {product_id, qty, unit_price, line_total}
    """
    session = SessionLocal()
    try:
        # Create Order
        db_order = Order(
            order_number=order_number,
            customer_id=customer_id,
            order_date=order_date,
            total_amount=total_amount,
            status='confirmed',
            created_by=created_by
        )
        session.add(db_order)
        session.flush()  # get id

        # Create Order Items & update stock, inventory logs
        for li in lines:
            oi = OrderItem(
                order_id=db_order.id,
                product_id=li['product_id'],
                qty=li['qty'],
                unit_price=li['unit_price'],
                line_total=li['line_total']
            )
            session.add(oi)

            # Update product stock & inventory log if product exists
            prod = session.query(Product).filter(Product.id == li['product_id']).first()
            if prod:
                prev = prod.current_stock or 0
                new = prev - li['qty']
                prod.current_stock = new
                log = InventoryLog(
                    product_id=prod.id,
                    change_qty=-li['qty'],
                    reason=f"Sales Order {order_number}",
                    prev_stock=prev,
                    new_stock=new
                )
                session.add(log)

        session.commit()
        return db_order.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# --- Streamlit UI ---
st.set_page_config(page_title="ERP Prototype", layout="wide")
st.markdown(
    """
    <style>
        .stApp { background: linear-gradient(180deg, #F7FAFF 0%, #FFFFFF 100%); }
        .header {text-align:center; padding:10px 0 20px 0}
        .card { background: white; border-radius:12px; padding:12px; box-shadow: 0 4px 18px rgba(79,129,189,0.08); }
        .muted { color:#6b7280; font-size:13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='header'><h1 style='color:#0B6FA4'>Amba ERP — Inventory & Sales</h1><div class='muted'>Professional prototype — Inventory validation, multi-price lines & SQL/DB output</div></div>", unsafe_allow_html=True)
st.markdown("---")

# Load products from DB; fallback to local excel if DB empty
prods = get_products_from_db()
if not prods:
    EXCEL_PATH = "management_report.xlsx"
    if os.path.exists(EXCEL_PATH):
        try:
            df_temp = pd.read_excel(EXCEL_PATH, sheet_name="Products")
            # convert to simple objects for UI
            prods = []
            for _, r in df_temp.iterrows():
                p = Product()
                p.id = int(r.get("id", 0))
                p.sku = r.get("sku", "")
                p.name = r.get("name", "")
                p.uom = r.get("uom", "pcs")
                p.current_stock = int(r.get("current_stock", 0))
                p.reorder_level = int(r.get("reorder_level", 0))
                p.price = float(r.get("price", 0.0))
                prods.append(p)
        except Exception:
            prods = []
# Build products DataFrame for display
if prods:
    df_products = pd.DataFrame([{
        "id": p.id,
        "sku": getattr(p, "sku", ""),
        "name": getattr(p, "name", ""),
        "uom": getattr(p, "uom", "pcs"),
        "current_stock": int(getattr(p, "current_stock", 0) or 0),
        "reorder_level": int(getattr(p, "reorder_level", 0) or 0),
        "price": float(getattr(p, "price", 0.0) or 0.0)
    } for p in prods])
else:
    df_products = pd.DataFrame([
        {"id": 1, "sku": "LAM-001", "name": "Lamination A", "uom": "pcs", "current_stock": 120, "reorder_level": 20, "price": 50.0},
        {"id": 2, "sku": "LAM-002", "name": "Lamination B", "uom": "pcs", "current_stock": 45,  "reorder_level": 10, "price": 75.0},
        {"id": 3, "sku": "STAMP-01", "name": "Motor Stamp 1", "uom": "pcs", "current_stock": 300, "reorder_level": 50, "price": 12.5},
    ])

# Layout
col1, col2 = st.columns([2, 3], gap="large")

with col1:
    st.markdown("<div class='card'><h3 style='color:#0B6FA4'>Inventory</h3>", unsafe_allow_html=True)
    # highlight low stock items
    def highlight_low(row):
        if row.current_stock <= row.reorder_level:
            return ['background-color: #fdecea']*len(row)
        return ['']*len(row)
    st.dataframe(df_products.style.apply(highlight_low, axis=1).format({"price": lambda v: money(v)}), height=420)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'><h3 style='color:#0B6FA4'>Create New Sales Order</h3>", unsafe_allow_html=True)

    # customers from DB
    customers = get_customers_from_db()
    if customers:
        cust_options = {c.name: c.id for c in customers}
    else:
        sample_customers = [{"id": 1, "name": "Amba Distributors"}, {"id": 2, "name": "TransCo Pvt Ltd"}]
        cust_options = {c['name']: c['id'] for c in sample_customers}

    with st.form("order_form", clear_on_submit=False):
        order_number = st.text_input("Order Number", value=f"ORD-{datetime.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}")
        customer_name = st.selectbox("Customer", options=list(cust_options.keys()))
        order_date = st.date_input("Order Date", value=datetime.date.today())
        created_by = st.text_input("Created by", value="operator")
        num_lines = st.number_input("Number of product lines", min_value=1, max_value=5, value=1, help="Add 1-5 different product lines")

        # Collect line inputs. Each *line* has one qty and up to 3 prices.
        # Price/qty logic: Qty applies to a line. Each non-zero price becomes a separate order item for the same qty.
        lines_collected = []
        product_names = df_products['name'].tolist()
        product_map = df_products.set_index('name').to_dict('index')

        # We'll collect a temporary dict of cumulative qty per product to validate stock
        required_by_product = {}

        for i in range(int(num_lines)):
            st.markdown(f"**Line {i+1}**")
            col_a, col_b = st.columns([2, 2])
            with col_a:
                prod_choice = st.selectbox(f"Product (line {i+1})", options=product_names, key=f"prod_{i}")
                qty = st.number_input(f"Qty (line {i+1})", min_value=1, value=1, key=f"qty_{i}")
            with col_b:
                st.write("Enter up to 3 unit prices for the same qty (leave blank or 0 to ignore):")
                default_price = float(product_map[prod_choice]['price']) if prod_choice in product_map else 0.0
                price1 = st.number_input(f"Price 1 (line {i+1})", min_value=0.0, value=float(default_price), key=f"price1_{i}")
                price2 = st.number_input(f"Price 2 (line {i+1})", min_value=0.0, value=0.0, key=f"price2_{i}")
                price3 = st.number_input(f"Price 3 (line {i+1})", min_value=0.0, value=0.0, key=f"price3_{i}")

            # Build line items from prices > 0
            for price in [price1, price2, price3]:
                if price is not None and float(price) > 0:
                    li = {
                        "product_id": int(product_map[prod_choice]['id']),
                        "product_name": prod_choice,
                        "qty": int(qty),
                        "unit_price": float(price),
                        "line_total": float(Decimal(qty) * Decimal(str(price)))
                    }
                    lines_collected.append(li)
                    # accumulate required qty for stock validation
                    required_by_product.setdefault(li['product_id'], 0)
                    required_by_product[li['product_id']] += li['qty']

        submitted = st.form_submit_button("Validate & Confirm Order")

    # When submitted: do client-side validation, show breakdown, write to DB
    if submitted:
        # Validate at least one line
        if not lines_collected:
            st.error("No valid price/qty entered — each line needs at least one price > 0.")
        else:
            # Validate stock availability (if product exists in DB)
            stock_issues = []
            # build quick lookup of db stocks from df_products
            stock_by_id = df_products.set_index('id')['current_stock'].to_dict()

            for pid, req_qty in required_by_product.items():
                available = stock_by_id.get(pid, None)
                if available is not None and req_qty > available:
                    stock_issues.append((pid, req_qty, available))
            if stock_issues:
                st.error("Stock validation failed for one or more products:")
                for pid, req, avail in stock_issues:
                    pname = df_products.loc[df_products['id'] == pid, 'name'].iloc[0]
                    st.write(f"- {pname}: required {req}, available {avail}")
            else:
                total_amount = sum([li['line_total'] for li in lines_collected])
                # display summary
                st.success(f"Validation passed — total = {money(total_amount)}")
                st.markdown("#### Order Summary")
                df_summary = pd.DataFrame([{
                    "Product": li['product_name'],
                    "Qty": li['qty'],
                    "Unit Price": money(li['unit_price']),
                    "Line Total": money(li['line_total'])
                } for li in lines_collected])
                st.table(df_summary)
                st.markdown(f"**Net Total:** {money(total_amount)}")

                # Show SQL statements (useful for review)
                st.markdown("### Generated SQL (preview)")
                st.code(f"INSERT INTO orders (order_number, customer_id, order_date, total_amount, status, created_by) VALUES ({sql_escape(order_number)}, {cust_options[customer_name]}, {sql_escape(order_date)}, {total_amount}, 'confirmed', {sql_escape(created_by)});")
                for li in lines_collected:
                    sql_line = f"INSERT INTO order_items (order_id, product_id, qty, unit_price, line_total) VALUES ((SELECT id FROM orders WHERE order_number={sql_escape(order_number)}), {sql_escape(li['product_id'])}, {sql_escape(li['qty'])}, {sql_escape(li['unit_price'])}, {sql_escape(li['line_total'])});"
                    st.code(sql_line)

                # Persist to DB (using SQLAlchemy models in models.py)
                try:
                    order_id = create_order_in_db(order_number, cust_options[customer_name], order_date, created_by, lines_collected, total_amount)
                    st.success(f"Order persisted to DB with id: {order_id}")
                except Exception as e:
                    st.error("Failed to persist order to DB. See error:")
                    st.exception(e)

    st.markdown("</div>", unsafe_allow_html=True)
