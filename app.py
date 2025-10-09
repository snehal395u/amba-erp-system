# app.py - FastAPI backend for auth + orders (uses models.py)
import os
from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt

import models
from models import SessionLocal, engine, User, Product, Customer, Order, OrderItem, InventoryLog

# Setup
models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Amba ERP API")

# CONFIG - change in production via env vars
SECRET_KEY = os.getenv("AMBA_SECRET_KEY", "change_this_secret_for_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    current_stock: int
    price: float

    class Config:
        orm_mode = True

class CustomerOut(BaseModel):
    id: int
    name: str
    class Config:
        orm_mode = True

class OrderLineIn(BaseModel):
    product_id: int
    qty: int
    unit_price: float

class OrderCreate(BaseModel):
    order_number: str
    customer_id: int
    order_date: datetime
    created_by: str
    lines: List[OrderLineIn]

class OrderOut(BaseModel):
    id: int
    order_number: str
    total_amount: float
    status: str
    class Config:
        orm_mode = True

# Utility
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid auth credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token or expired")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Seed a default admin (for demo)
@app.on_event("startup")
def seed_default_user():
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(username="admin", hashed_password=get_password_hash("admin123"))
        db.add(admin)
        db.commit()
    # add some sample customers & products if missing
    if db.query(Customer).count() == 0:
        db.add_all([Customer(name="Amba Distributors"), Customer(name="TransCo Pvt Ltd")])
    if db.query(Product).count() == 0:
        db.add_all([
            Product(sku="LAM-001", name="Lamination A", uom="pcs", current_stock=120, reorder_level=20, price=50.0),
            Product(sku="LAM-002", name="Lamination B", uom="pcs", current_stock=45, reorder_level=10, price=75.0),
            Product(sku="STAMP-01", name="Motor Stamp 1", uom="pcs", current_stock=300, reorder_level=50, price=12.5),
        ])
    db.commit()
    db.close()

# Auth token endpoint
@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# Public endpoints for products/customers
@app.get("/products", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    products = db.query(Product).all()
    return products

@app.get("/customers", response_model=List[CustomerOut])
def list_customers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Customer).all()

# Create order
@app.post("/orders", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Basic validations
    if db.query(Order).filter(Order.order_number == payload.order_number).first():
        raise HTTPException(status_code=400, detail="Order number already exists")
    cust = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not cust:
        raise HTTPException(status_code=400, detail="Customer not found")

    total_amount = 0
    for line in payload.lines:
        prod = db.query(Product).filter(Product.id == line.product_id).first()
        if not prod:
            raise HTTPException(status_code=400, detail=f"Product id {line.product_id} not found")
        if line.qty <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be > 0")
        if line.qty > prod.current_stock:
            raise HTTPException(status_code=400, detail=f"Not enough stock for product {prod.name} (available {prod.current_stock})")
        total_amount += float(line.qty) * float(line.unit_price)

    # create order
    order = Order(order_number=payload.order_number, customer_id=payload.customer_id,
                  order_date=payload.order_date.date(), total_amount=total_amount,
                  status="confirmed", created_by=payload.created_by)
    db.add(order)
    db.flush()  # to get order.id

    # create order lines and update stock & inventory log
    for line in payload.lines:
        line_total = float(line.qty) * float(line.unit_price)
        oi = OrderItem(order_id=order.id, product_id=line.product_id, qty=line.qty, unit_price=line.unit_price, line_total=line_total)
        db.add(oi)
        # update product stock
        prod = db.query(Product).filter(Product.id == line.product_id).with_for_update().first()
        prev_stock = prod.current_stock
        prod.current_stock = prod.current_stock - line.qty
        inv = InventoryLog(product_id=prod.id, change_qty=-line.qty, reason=f"Sale {order.order_number}", prev_stock=prev_stock, new_stock=prod.current_stock)
        db.add(inv)

    db.commit()
    db.refresh(order)
    return order

# Simple read orders
@app.get("/orders", response_model=List[OrderOut])
def list_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Order).order_by(Order.id.desc()).all()
