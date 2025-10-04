# models.py - SQLAlchemy models (SQLite by default for local testing)
from sqlalchemy import Column, Integer, String, Numeric, Date, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date

DATABASE_URL = "sqlite:///./amba_erp.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    uom = Column(String(32))
    current_stock = Column(Integer, default=0)
    reorder_level = Column(Integer, default=0)
    price = Column(Numeric(12,2), default=0.0)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    order_date = Column(Date)
    total_amount = Column(Numeric(14,2), default=0.0)
    status = Column(String(50), default='draft')
    created_by = Column(String(255))

class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    qty = Column(Integer)
    unit_price = Column(Numeric(12,2))
    line_total = Column(Numeric(14,2))

class InventoryLog(Base):
    __tablename__ = 'inventory_log'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    change_qty = Column(Integer)
    reason = Column(String(255))
    prev_stock = Column(Integer)
    new_stock = Column(Integer)

if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)
