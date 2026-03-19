from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel, Field
from typing import Optional, List
import math

app = FastAPI()

# ─────────────────────────────────────────────
# Sample Data
# ─────────────────────────────────────────────

products = [
    {"id": 1, "name": "Wireless Mouse",  "price": 499, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook",         "price": 99,  "category": "Stationery",  "in_stock": True},
    {"id": 3, "name": "USB Hub",          "price": 799, "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set",          "price": 49,  "category": "Stationery",  "in_stock": True},
]

orders        = []
feedback      = []
order_counter = {"count": 0}

# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class NewProduct(BaseModel):
    name:     str  = Field(..., min_length=1)
    price:    int  = Field(..., gt=0)
    category: str  = Field(..., min_length=1)
    in_stock: bool = True

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)   # ← added for Q4 order search
    product_id:    int = Field(..., gt=0)
    quantity:      int = Field(..., gt=0, le=100)

class CustomerFeedback(BaseModel):
    customer_name: str           = Field(..., min_length=2, max_length=100)
    product_id:    int           = Field(..., gt=0)
    rating:        int           = Field(..., ge=1, le=5)
    comment:       Optional[str] = Field(None, max_length=300)

class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity:   int = Field(..., gt=0, le=50)

class BulkOrder(BaseModel):
    company_name:  str             = Field(..., min_length=2)
    contact_email: str             = Field(..., min_length=5)
    items:         List[OrderItem] = Field(..., min_length=1)

# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def find_product(product_id: int):
    return next((p for p in products if p["id"] == product_id), None)

# ─────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Welcome to the FastAPI Store!"}

# ═══════════════════════════════════════════════
# PRODUCT ENDPOINTS
# All fixed routes MUST come before /{product_id}
# ═══════════════════════════════════════════════

# ── GET /products ────────────────────────────

@app.get("/products")
def get_all_products():
    return {"products": products, "total": len(products)}

# ── GET /products/filter ─────────────────────

@app.get("/products/filter")
def filter_products(
    category:  str = Query(None, description="Filter by category"),
    max_price: int = Query(None, description="Maximum price"),
    min_price: int = Query(None, description="Minimum price"),
):
    result = products
    if category:
        result = [p for p in result if p["category"].lower() == category.lower()]
    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]
    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]
    return {"filtered_products": result, "count": len(result)}

# ── GET /products/summary ────────────────────

@app.get("/products/summary")
def product_summary():
    in_stock   = [p for p in products if     p["in_stock"]]
    out_stock  = [p for p in products if not p["in_stock"]]
    expensive  = max(products, key=lambda p: p["price"])
    cheapest   = min(products, key=lambda p: p["price"])
    categories = list(set(p["category"] for p in products))
    return {
        "total_products":     len(products),
        "in_stock_count":     len(in_stock),
        "out_of_stock_count": len(out_stock),
        "most_expensive":     {"name": expensive["name"], "price": expensive["price"]},
        "cheapest":           {"name": cheapest["name"],  "price": cheapest["price"]},
        "categories":         categories,
    }

# ── GET /products/audit ──────────────────────

@app.get("/products/audit")
def product_audit():
    in_stock_list  = [p for p in products if     p["in_stock"]]
    out_stock_list = [p for p in products if not p["in_stock"]]
    stock_value    = sum(p["price"] * 10 for p in in_stock_list)
    priciest       = max(products, key=lambda p: p["price"])
    return {
        "total_products":     len(products),
        "in_stock_count":     len(in_stock_list),
        "out_of_stock_names": [p["name"] for p in out_stock_list],
        "total_stock_value":  stock_value,
        "most_expensive":     {"name": priciest["name"], "price": priciest["price"]},
    }

# ── Q1 — GET /products/search ────────────────

@app.get("/products/search")
def search_products(keyword: str = Query(..., description="Search keyword")):
    results = [p for p in products if keyword.lower() in p["name"].lower()]
    if not results:
        return {"message": f"No products found for: {keyword}"}
    return {"keyword": keyword, "total_found": len(results), "products": results}

# ── Q2 — GET /products/sort ──────────────────

@app.get("/products/sort")
def sort_products(
    sort_by: str = Query("price", description="Sort by 'price' or 'name'"),
    order:   str = Query("asc",   description="'asc' or 'desc'"),
):
    if sort_by not in ["price", "name"]:
        return {"error": "sort_by must be 'price' or 'name'"}

    reverse = (order == "desc")
    result  = sorted(products, key=lambda p: p[sort_by], reverse=reverse)
    return {"sort_by": sort_by, "order": order, "products": result}

# ── Q3 — GET /products/page ──────────────────

@app.get("/products/page")
def get_products_paged(
    page:  int = Query(1, ge=1,  description="Page number (starts at 1)"),
    limit: int = Query(2, ge=1, le=20, description="Items per page"),
):
    start       = (page - 1) * limit
    paged       = products[start: start + limit]
    total_pages = -(-len(products) // limit)   # ceiling division
    return {
        "page":        page,
        "limit":       limit,
        "total":       len(products),
        "total_pages": total_pages,
        "products":    paged,
    }

# ── Q5 — GET /products/sort-by-category ──────

@app.get("/products/sort-by-category")
def sort_by_category():
    # Sort by category (A→Z) first, then price (asc) within each category
    result = sorted(products, key=lambda p: (p["category"], p["price"]))
    return {"products": result, "total": len(result)}

# ── Q6 — GET /products/browse ────────────────
# Combines search + sort + pagination in one endpoint

@app.get("/products/browse")
def browse_products(
    keyword: str = Query(None,    description="Search keyword (optional)"),
    sort_by: str = Query("price", description="'price' or 'name'"),
    order:   str = Query("asc",   description="'asc' or 'desc'"),
    page:    int = Query(1,  ge=1,       description="Page number"),
    limit:   int = Query(4,  ge=1, le=20, description="Items per page"),
):
    # Step 1 — Filter by keyword
    result = products
    if keyword:
        result = [p for p in result if keyword.lower() in p["name"].lower()]

    # Step 2 — Sort
    if sort_by in ["price", "name"]:
        result = sorted(result, key=lambda p: p[sort_by], reverse=(order == "desc"))

    # Step 3 — Paginate
    total       = len(result)
    start       = (page - 1) * limit
    paged       = result[start: start + limit]
    total_pages = -(-total // limit) if total > 0 else 0

    return {
        "keyword":     keyword,
        "sort_by":     sort_by,
        "order":       order,
        "page":        page,
        "limit":       limit,
        "total_found": total,
        "total_pages": total_pages,
        "products":    paged,
    }

# ── GET /products/{product_id} ───────────────
# ⚠️  All fixed routes MUST be above this one

@app.get("/products/{product_id}")
def get_product(product_id: int, response: Response):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    return {"product": product}

# ── GET /products/{product_id}/price ─────────

@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    product = find_product(product_id)
    if not product:
        return {"error": "Product not found"}
    return {"name": product["name"], "price": product["price"]}

# ── POST /products ────────────────────────────

@app.post("/products", status_code=status.HTTP_201_CREATED)
def add_product(new_product: NewProduct, response: Response):
    for p in products:
        if p["name"].lower() == new_product.name.lower():
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"error": f"Product '{new_product.name}' already exists"}

    next_id = max(p["id"] for p in products) + 1
    product = {
        "id":       next_id,
        "name":     new_product.name,
        "price":    new_product.price,
        "category": new_product.category,
        "in_stock": new_product.in_stock,
    }
    products.append(product)
    return {"message": "Product added", "product": product}

# ── PUT /products/discount ────────────────────
# ⚠️  Must be above PUT /products/{product_id}

@app.put("/products/discount")
def bulk_discount(
    category:         str = Query(..., description="Category to discount"),
    discount_percent: int = Query(..., ge=1, le=99, description="Discount % (1-99)"),
):
    updated = []
    for p in products:
        if p["category"].lower() == category.lower():
            p["price"] = int(p["price"] * (1 - discount_percent / 100))
            updated.append(p)
    if not updated:
        return {"message": f"No products found in category: {category}"}
    return {
        "message":          f"{discount_percent}% discount applied to {category}",
        "updated_count":    len(updated),
        "updated_products": updated,
    }

# ── PUT /products/{product_id} ────────────────

@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    response:   Response,
    price:      Optional[int]  = Query(None, gt=0),
    in_stock:   Optional[bool] = Query(None),
):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    if price is not None:
        product["price"] = price
    if in_stock is not None:
        product["in_stock"] = in_stock
    return {"message": "Product updated", "product": product}

# ── DELETE /products/{product_id} ────────────

@app.delete("/products/{product_id}")
def delete_product(product_id: int, response: Response):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
    products.remove(product)
    return {"message": f"Product '{product['name']}' deleted"}

# ═══════════════════════════════════════════════
# ORDER ENDPOINTS
# ═══════════════════════════════════════════════

# ── POST /orders ──────────────────────────────

@app.post("/orders")
def place_order(order_req: OrderRequest):
    product = find_product(order_req.product_id)
    if not product:
        return {"error": "Product not found"}
    if not product["in_stock"]:
        return {"error": f"{product['name']} is out of stock"}

    order_counter["count"] += 1
    new_order = {
        "order_id":     order_counter["count"],
        "customer_name": order_req.customer_name,
        "product":      product["name"],
        "quantity":     order_req.quantity,
        "total":        product["price"] * order_req.quantity,
        "status":       "pending",
    }
    orders.append(new_order)
    return {"message": "Order placed successfully", "order": new_order}

# ── Q4 — GET /orders/search ──────────────────
# ⚠️  Must be above GET /orders/{order_id}

@app.get("/orders/search")
def search_orders(customer_name: str = Query(..., description="Customer name to search")):
    results = [
        o for o in orders
        if customer_name.lower() in o["customer_name"].lower()
    ]
    if not results:
        return {"message": f"No orders found for: {customer_name}"}
    return {
        "customer_name": customer_name,
        "total_found":   len(results),
        "orders":        results,
    }

# ── BONUS — GET /orders/page ──────────────────
# ⚠️  Must be above GET /orders/{order_id}

@app.get("/orders/page")
def get_orders_paged(
    page:  int = Query(1, ge=1,       description="Page number"),
    limit: int = Query(3, ge=1, le=20, description="Items per page"),
):
    start       = (page - 1) * limit
    total_pages = -(-len(orders) // limit) if orders else 0
    return {
        "page":        page,
        "limit":       limit,
        "total":       len(orders),
        "total_pages": total_pages,
        "orders":      orders[start: start + limit],
    }

# ── GET /orders/{order_id} ────────────────────

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            return {"order": order}
    return {"error": "Order not found"}

# ── PATCH /orders/{order_id}/confirm ─────────

@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            order["status"] = "confirmed"
            return {"message": "Order confirmed", "order": order}
    return {"error": "Order not found"}

# ── POST /orders/bulk ─────────────────────────

@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):
    confirmed, failed, grand_total = [], [], 0
    for item in order.items:
        product = find_product(item.product_id)
        if not product:
            failed.append({"product_id": item.product_id, "reason": "Product not found"})
        elif not product["in_stock"]:
            failed.append({"product_id": item.product_id, "reason": f"{product['name']} is out of stock"})
        else:
            subtotal = product["price"] * item.quantity
            grand_total += subtotal
            confirmed.append({"product": product["name"], "qty": item.quantity, "subtotal": subtotal})
    return {
        "company":     order.company_name,
        "confirmed":   confirmed,
        "failed":      failed,
        "grand_total": grand_total,
    }

# ═══════════════════════════════════════════════
# FEEDBACK ENDPOINTS
# ═══════════════════════════════════════════════

@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    feedback.append(data.dict())
    return {
        "message":        "Feedback submitted successfully",
        "feedback":       data.dict(),
        "total_feedback": len(feedback),
    }