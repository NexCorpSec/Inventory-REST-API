from flask import Flask, jsonify, request, abort
from models import db, Product, Category, Supplier
from services.inventory_service import InventoryService
from services.alert_service import AlertService
from middleware.auth import require_api_key
from middleware.rate_limiter import rate_limit
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object("config.ProductionConfig")

db.init_app(app)
inventory_service = InventoryService()
alert_service = AlertService()


@app.before_request
def log_request():
    logger.info(f"[{request.method}] {request.path} — from {request.remote_addr}")


# ── Products ──────────────────────────────────────────────

@app.route("/api/v1/products", methods=["GET"])
@require_api_key
@rate_limit(max_requests=100, window_seconds=60)
def list_products():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category_id = request.args.get("category_id", type=int)
    low_stock = request.args.get("low_stock", False, type=bool)

    products = inventory_service.get_products(
        page=page,
        per_page=per_page,
        category_id=category_id,
        low_stock_only=low_stock,
    )
    return jsonify(products)


@app.route("/api/v1/products/<int:product_id>", methods=["GET"])
@require_api_key
def get_product(product_id):
    product = inventory_service.get_product_by_id(product_id)
    if not product:
        abort(404, description="Product not found")
    return jsonify(product)


@app.route("/api/v1/products", methods=["POST"])
@require_api_key
def create_product():
    data = request.get_json(force=True)
    errors = inventory_service.validate_product(data)
    if errors:
        return jsonify({"errors": errors}), 422

    product = inventory_service.create_product(data)
    logger.info(f"Created product id={product['id']}")
    return jsonify(product), 201


@app.route("/api/v1/products/<int:product_id>", methods=["PATCH"])
@require_api_key
def update_product(product_id):
    data = request.get_json(force=True)
    product = inventory_service.update_product(product_id, data)
    if not product:
        abort(404, description="Product not found")
    return jsonify(product)


@app.route("/api/v1/products/<int:product_id>/restock", methods=["POST"])
@require_api_key
def restock_product(product_id):
    data = request.get_json(force=True)
    quantity = data.get("quantity", 0)
    if quantity <= 0:
        abort(400, description="Quantity must be a positive integer")

    result = inventory_service.restock(product_id, quantity)
    alert_service.clear_low_stock_alert(product_id)
    return jsonify(result)


# ── Categories ────────────────────────────────────────────

@app.route("/api/v1/categories", methods=["GET"])
@require_api_key
def list_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])


# ── Suppliers ─────────────────────────────────────────────

@app.route("/api/v1/suppliers", methods=["GET"])
@require_api_key
def list_suppliers():
    suppliers = Supplier.query.all()
    return jsonify([s.to_dict() for s in suppliers])


@app.route("/api/v1/suppliers/<int:supplier_id>/products", methods=["GET"])
@require_api_key
def get_supplier_products(supplier_id):
    products = inventory_service.get_products_by_supplier(supplier_id)
    return jsonify(products)


# ── Reports ───────────────────────────────────────────────

@app.route("/api/v1/reports/low-stock", methods=["GET"])
@require_api_key
def low_stock_report():
    threshold = request.args.get("threshold", 10, type=int)
    report = inventory_service.generate_low_stock_report(threshold)
    return jsonify(report)


@app.route("/api/v1/reports/valuation", methods=["GET"])
@require_api_key
def valuation_report():
    report = inventory_service.generate_valuation_report()
    return jsonify(report)


# ── Health ────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": str(e)}), 404


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(422)
def unprocessable(e):
    return jsonify({"error": str(e)}), 422


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
