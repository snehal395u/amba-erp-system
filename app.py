# app.py - FastAPI backend example
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from models import SessionLocal, Product, Order, OrderItem, InventoryLog
from sqlalchemy.orm import Session
from datetime import datetime

app = FastAPI(title="Amba ERP API")

class OrderLinePayload(BaseModel):
    product_id: int
    qty: int
    unit_price: float

class OrderPayload(BaseModel):
    order_number: str
    customer_id: int
    order_date: str
    lines: List[OrderLinePayload]
    created_by: str = "operator"

@app.post("/api/v1/orders")
def create_order(payload: OrderPayload):
    db: Session = SessionLocal()
    try:
        with db.begin():
            order = Order(order_number=payload.order_number,
                          customer_id=payload.customer_id,
                          order_date=payload.order_date,
                          status='confirmed',
                          total_amount=0.0,
                          created_by=payload.created_by)
            db.add(order)
            db.flush()
            total = 0.0
            for line in payload.lines:
                prod = db.query(Product).filter(Product.id == line.product_id).with_for_update().one_or_none()
                if prod is None:
                    raise HTTPException(status_code=400, detail=f"Product {line.product_id} not found")
                if prod.current_stock < line.qty:
                    raise HTTPException(status_code=409, detail=f"Insufficient stock for product {prod.id}")
                prev = prod.current_stock
                prod.current_stock -= line.qty
                new = prod.current_stock
                line_total = line.qty * line.unit_price
                oi = OrderItem(order_id=order.id, product_id=prod.id, qty=line.qty, unit_price=line.unit_price, line_total=line_total)
                db.add(oi)
                il = InventoryLog(product_id=prod.id, change_qty=-line.qty, reason=f"order:{order.order_number}", prev_stock=prev, new_stock=new)
                db.add(il)
                total += line_total
            order.total_amount = total
            db.add(order)
        return {"order_id": order.id, "order_number": order.order_number, "total_amount": order.total_amount}
    finally:
        db.close()
