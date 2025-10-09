# app.py - FastAPI endpoints for auth and orders (prototype)
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, condecimal
from typing import List, Optional
from models import SessionLocal, User, Product, Customer, Order, OrderItem, InventoryLog
from datetime import date, datetime, timedelta
import secrets

app = FastAPI(title="Amba ERP API (Prototype)")

# --- Simple in-memory token store (prototype only) ---
TOKENS = {}  # token -> {"user_id": id, "expires": datetime}

def create_token(user_id: int):
    token = secrets.token_urlsafe(24)
    TOKENS[token] = {"user_id": user_id, "expires": datetime.utcnow() + timedelta(hours=8)}
    return token

def verify_token(auth_header: Optional[str]):
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    token = auth_header.split(" ", 1)[1]
    record = TOKENS.get(token)
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if record["expires"] < datetime.utcnow():
        TOKENS.pop(token, None)
        raise HTTPException(status_code=401, detail="Token expired")
    return record["user_id"]

# --- Pydantic schemas ---
class LoginIn(BaseModel):
    username: str
    password: str

class OrderLineIn(BaseModel):
    product_id: int
    qty: int
    unit_price: condecimal(max_digits=14, decimal_places=2)

class OrderIn(BaseModel):
    order_number: Optional[str] = None
    customer_id: int
    order_date: Optional[date] = None
    created_by: Optional[str] = "api_user"
    lines: List[OrderLineIn]

class ProductOut(BaseModel):
    id: int
    sku: Optional[str]
    name: str
    uom: Optional[str]
    current_stock: Optional[int]
    reorder_level: Optional[int]
    price: Optional[condecimal(max_digits=12, decimal_places=2)]

class OrderOut(BaseModel):
    id: int
    order_number: str
    customer_id: int
    order_date: Optional[date]
    total_amount: float
    status: str
    created_by: Optional[str]

# --- Auth endpoint ---
@app.post("/auth/login")
def login(payload: LoginIn):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == payload.username).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # PROTOTYPE: compare plaintext; replace with proper hashing in prod
        if payload.password != user.hashed_password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_token(user.id)
        return {"access_token": token, "token_type": "bearer"}
    finally:
        session.close()

# --- Products / Customers endpoints ---
@app.get("/products", response_model=List[ProductOut])
def list_products():
    session = SessionLocal()
    try:
        prods = session.query(Product).order_by(Product.id).all()
        return prods
    finally:
        session.close()

@app.get("/customers")
def list_customers():
    session = SessionLocal()
    try:
        custs = session.query(Customer).order_by(Customer.id).all()
        return [{"id": c.id, "name": c.name} for c in custs]
    finally:
        session.close()

# --- Orders endpoints ---
@app.post("/orders", response_model=dict)
def create_order(payload: OrderIn, authorization: Optional[str] = Header(None)):
    user_id = verify_token(authorization)
    session = SessionLocal()
    try:
        # build order number if not provided
        order_number = payload.order_number or f"ORD-{date.today().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
        order_date = payload.order_date or date.today()
        total_amount = sum([float(l.qty) * float(l.unit_price) for l in payload.lines])

        db_order = Order(
            order_number=order_number,
            customer_id=payload.customer_id,
            order_date=order_date,
            total_amount=total_amount,
            status='confirmed',
            created_by=payload.created_by
        )
        session.add(db_order)
        session.flush()

        # Stock validation
        required = {}
        for l in payload.lines:
            required.setdefault(l.product_id, 0)
            required[l.product_id] += l.qty
        # Check availability
        for pid, rq in required.items():
            prod = session.query(Product).filter(Product.id == pid).first()
            if prod and (prod.current_stock is not None) and rq > prod.current_stock:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for product id {pid} (required {rq}, available {prod.current_stock})")

        # Create order items & update stock/logs
        for l in payload.lines:
            line_total = float(l.qty) * float(l.unit_price)
            oi = OrderItem(
                order_id=db_order.id,
                product_id=l.product_id,
                qty=l.qty,
                unit_price=l.unit_price,
                line_total=line_total
            )
            session.add(oi)

            prod = session.query(Product).filter(Product.id == l.product_id).first()
            if prod:
                prev = prod.current_stock or 0
                prod.current_stock = prev - l.qty
                log = InventoryLog(
                    product_id=prod.id,
                    change_qty=-l.qty,
                    reason=f"API Sales Order {order_number}",
                    prev_stock=prev,
                    new_stock=prod.current_stock
                )
                session.add(log)

        session.commit()
        return {"order_id": db_order.id, "order_number": order_number}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/orders", response_model=List[OrderOut])
def list_orders(authorization: Optional[str] = Header(None)):
    user_id = verify_token(authorization)
    session = SessionLocal()
    try:
        rows = session.query(Order).order_by(Order.id.desc()).all()
        return rows
    finally:
        session.close()

@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, authorization: Optional[str] = Header(None)):
    user_id = verify_token(authorization)
    session = SessionLocal()
    try:
        o = session.query(Order).filter(Order.id == order_id).first()
        if not o:
            raise HTTPException(status_code=404, detail="Order not found")
        return o
    finally:
        session.close()
