# inventory-api

A REST API for managing product inventory, stock levels, suppliers, and restock alerts.

## Stack
- Python 3.11+
- Flask 3
- SQLAlchemy (PostgreSQL in production, SQLite for dev)

## Quickstart

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost/inventory
export SECRET_KEY=your-secret
python app.py
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/products | List products (paginated) |
| POST | /api/v1/products | Create product |
| GET | /api/v1/products/:id | Get product |
| PATCH | /api/v1/products/:id | Update product |
| POST | /api/v1/products/:id/restock | Add stock |
| GET | /api/v1/categories | List categories |
| GET | /api/v1/suppliers | List suppliers |
| GET | /api/v1/reports/low-stock | Low stock report |
| GET | /api/v1/reports/valuation | Inventory valuation |

All endpoints require an `X-API-Key` header.
