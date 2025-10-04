<<<<<<< HEAD
# app.py - FastAPI ERP Backend with JWT + Orders + Inventory

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

from models import User, Product, Order, OrderItem, InventoryLog, SessionLocal

# JWT Configuration
SECRET_KEY = "super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# FastAPI instance
app = FastAPI(
    title="Amba ERP API",
    description="ERP Backend with JWT authentication, Orders, Inventory, and Customers",
    version="1.0.0"
)

# -----------------------------
# Utility functions
# -----------------------------
def verify_password(plain, hashed): 
    return pwd_context.verify(plain, hashed)

def hash_password(password): 
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# Pydantic Models for Orders
# -----------------------------
class OrderLinePayload(BaseModel):
    product_id: int
    qty: int
    unit_price: float
=======
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models import User
from database import get_db

SECRET_KEY = "super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
>>>>>>> e31f0d83f61fecad1526199e5798bced32edcaa0

app = FastAPI(
    title="Amba ERP API",
    description="ERP Backend with JWT authentication, Orders, Inventory, and Customers",
    version="1.0.0"
)

<<<<<<< HEAD
# -----------------------------
# Authentication endpoints
# -----------------------------
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
=======
def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)
def hash_password(p): return pwd_context.hash(p)

def create_access_token(data: dict, expires_delta: timedelta = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
>>>>>>> e31f0d83f61fecad1526199e5798bced32edcaa0
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me")
<<<<<<< HEAD
def read_users_me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}

# -----------------------------
# Orders endpoint (JWT-protected)
# -----------------------------
@app.post("/api/v1/orders")
def create_order(payload: OrderPayload, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        with db.begin():
            # Create Order
            order = Order(
                order_number=payload.order_number,
                customer_id=payload.customer_id,
                order_date=payload.order_date,
                status="confirmed",
                total_amount=0.0,
                created_by=current_user
            )
            db.add(order)
            db.flush()  # get order.id

            total_amount = 0.0
            for line in payload.lines:
                product = db.query(Product).filter(Product.id == line.product_id).with_for_update().one_or_none()
                if not product:
                    raise HTTPException(status_code=400, detail=f"Product {line.product_id} not found")
                if product.current_stock < line.qty:
                    raise HTTPException(status_code=409, detail=f"Insufficient stock for product {product.id}")

                prev_stock = product.current_stock
                product.current_stock -= line.qty
                new_stock = product.current_stock

                line_total = line.qty * line.unit_price
                total_amount += line_total

                # Add OrderItem
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    qty=line.qty,
                    unit_price=line.unit_price,
                    line_total=line_total
                )
                db.add(order_item)

                # Add Inventory Log
                inv_log = InventoryLog(
                    product_id=product.id,
                    change_qty=-line.qty,
                    reason=f"order:{order.order_number}",
                    prev_stock=prev_stock,
                    new_stock=new_stock
                )
                db.add(inv_log)

            order.total_amount = total_amount
            db.add(order)
        return {"order_id": order.id, "order_number": order.order_number, "total_amount": total_amount}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
=======
def me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload.get("sub")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
>>>>>>> e31f0d83f61fecad1526199e5798bced32edcaa0
