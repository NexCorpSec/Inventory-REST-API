from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Category(TimestampMixin, db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    products = db.relationship("Product", back_populates="category", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "product_count": self.products.count(),
            "created_at": self.created_at.isoformat(),
        }


class Supplier(TimestampMixin, db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(20))
    country = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    products = db.relationship("Product", back_populates="supplier", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "contact_email": self.contact_email,
            "phone": self.phone,
            "country": self.country,
            "active": self.active,
        }


class Product(TimestampMixin, db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    cost_price = db.Column(db.Numeric(10, 2))
    quantity = db.Column(db.Integer, default=0, nullable=False)
    reorder_point = db.Column(db.Integer, default=10)
    weight_kg = db.Column(db.Float)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    active = db.Column(db.Boolean, default=True)

    category = db.relationship("Category", back_populates="products")
    supplier = db.relationship("Supplier", back_populates="products")
    stock_movements = db.relationship("StockMovement", back_populates="product", lazy="dynamic")

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_point

    @property
    def margin(self):
        if self.cost_price and self.price:
            return round((float(self.price) - float(self.cost_price)) / float(self.price) * 100, 2)
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),
            "cost_price": float(self.cost_price) if self.cost_price else None,
            "margin_pct": self.margin,
            "quantity": self.quantity,
            "reorder_point": self.reorder_point,
            "is_low_stock": self.is_low_stock,
            "weight_kg": self.weight_kg,
            "category": self.category.name if self.category else None,
            "supplier": self.supplier.name if self.supplier else None,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # 'restock', 'sale', 'adjustment', 'return'
    quantity_delta = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)
    reference_id = db.Column(db.String(100))  # order ID, PO number, etc.
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product = db.relationship("Product", back_populates="stock_movements")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "movement_type": self.movement_type,
            "quantity_delta": self.quantity_delta,
            "quantity_after": self.quantity_after,
            "reference_id": self.reference_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
