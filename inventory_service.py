from models import db, Product, StockMovement
from sqlalchemy import func
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class InventoryService:

    def get_products(self, page=1, per_page=20, category_id=None, low_stock_only=False):
        query = Product.query.filter_by(active=True)

        if category_id:
            query = query.filter_by(category_id=category_id)

        if low_stock_only:
            query = query.filter(Product.quantity <= Product.reorder_point)

        paginated = query.order_by(Product.name).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "items": [p.to_dict() for p in paginated.items],
            "total": paginated.total,
            "page": paginated.page,
            "pages": paginated.pages,
            "per_page": per_page,
        }

    def get_product_by_id(self, product_id):
        product = Product.query.get(product_id)
        return product.to_dict() if product else None

    def get_products_by_supplier(self, supplier_id):
        products = Product.query.filter_by(supplier_id=supplier_id, active=True).all()
        return [p.to_dict() for p in products]

    def validate_product(self, data):
        errors = []
        required = ["sku", "name", "price", "category_id"]
        for field in required:
            if field not in data or data[field] is None:
                errors.append(f"'{field}' is required")

        if "price" in data and data["price"] is not None:
            try:
                if float(data["price"]) < 0:
                    errors.append("'price' must be non-negative")
            except (ValueError, TypeError):
                errors.append("'price' must be a number")

        if "sku" in data and Product.query.filter_by(sku=data["sku"]).first():
            errors.append(f"SKU '{data['sku']}' already exists")

        return errors

    def create_product(self, data):
        product = Product(
            sku=data["sku"],
            name=data["name"],
            description=data.get("description"),
            price=data["price"],
            cost_price=data.get("cost_price"),
            quantity=data.get("quantity", 0),
            reorder_point=data.get("reorder_point", 10),
            weight_kg=data.get("weight_kg"),
            category_id=data["category_id"],
            supplier_id=data.get("supplier_id"),
        )
        db.session.add(product)
        db.session.commit()
        logger.info(f"Product created: {product.sku}")
        return product.to_dict()

    def update_product(self, product_id, data):
        product = Product.query.get(product_id)
        if not product:
            return None

        allowed_fields = ["name", "description", "price", "cost_price", "reorder_point", "weight_kg", "active"]
        for field in allowed_fields:
            if field in data:
                setattr(product, field, data[field])

        db.session.commit()
        return product.to_dict()

    def restock(self, product_id, quantity):
        product = Product.query.get(product_id)
        if not product:
            return None

        old_qty = product.quantity
        product.quantity += quantity

        movement = StockMovement(
            product_id=product_id,
            movement_type="restock",
            quantity_delta=quantity,
            quantity_after=product.quantity,
            notes=f"Manual restock from {old_qty} to {product.quantity}",
        )
        db.session.add(movement)
        db.session.commit()

        logger.info(f"Restocked product {product_id}: +{quantity} units")
        return {"product_id": product_id, "new_quantity": product.quantity}

    def generate_low_stock_report(self, threshold=10):
        products = Product.query.filter(
            Product.quantity <= threshold,
            Product.active == True,
        ).order_by(Product.quantity.asc()).all()

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "threshold": threshold,
            "count": len(products),
            "products": [
                {
                    "id": p.id,
                    "sku": p.sku,
                    "name": p.name,
                    "quantity": p.quantity,
                    "reorder_point": p.reorder_point,
                    "supplier": p.supplier.name if p.supplier else None,
                }
                for p in products
            ],
        }

    def generate_valuation_report(self):
        products = Product.query.filter_by(active=True).all()
        total_retail = sum(float(p.price) * p.quantity for p in products)
        total_cost = sum(float(p.cost_price or 0) * p.quantity for p in products)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "total_skus": len(products),
            "total_units": sum(p.quantity for p in products),
            "total_retail_value": round(total_retail, 2),
            "total_cost_value": round(total_cost, 2),
            "estimated_gross_profit": round(total_retail - total_cost, 2),
        }
