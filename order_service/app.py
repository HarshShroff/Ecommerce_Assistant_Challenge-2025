# order_service/app.py
import os
import sys

# ensure project root (where mock_api/ lives) is on PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, jsonify
from mock_api_client import (
    get_all_data,
    get_customer_data,
    get_product_category_data,
    get_orders_by_priority,
    total_sales_by_category,
    high_profit_products,
    shipping_cost_summary,
    profit_by_gender,
)

app = Flask(__name__)

def _maybe_error(resp):
    if isinstance(resp, dict) and "error" in resp:
        return jsonify(resp), 404
    return jsonify(resp)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})

@app.route("/data", methods=["GET"])
def route_all_data():
    return _maybe_error(get_all_data())

@app.route("/data/customer/<int:customer_id>", methods=["GET"])
def route_customer(customer_id):
    return _maybe_error(get_customer_data(customer_id))

@app.route("/data/product-category/<string:category>", methods=["GET"])
def route_by_category(category):
    return _maybe_error(get_product_category_data(category))

@app.route("/data/order-priority/<string:priority>", methods=["GET"])
def route_by_priority(priority):
    return _maybe_error(get_orders_by_priority(priority))

@app.route("/data/total-sales-by-category", methods=["GET"])
def route_sales_summary():
    return _maybe_error(total_sales_by_category())

@app.route("/data/high-profit-products", methods=["GET"])
def route_high_profit():
    return _maybe_error(high_profit_products())

@app.route("/data/shipping-cost-summary", methods=["GET"])
def route_shipping_summary():
    return jsonify(shipping_cost_summary())

@app.route("/data/profit-by-gender", methods=["GET"])
def route_profit_by_gender():
    return _maybe_error(profit_by_gender())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
