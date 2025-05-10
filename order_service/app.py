# order_service/app.py

import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

from flask import Flask, jsonify, make_response
from flask_restful import Resource, Api
from flasgger import Swagger

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
api = Api(app)
swagger = Swagger(app)

def _maybe_error(resp):
    # if the client library returned an error dict, wrap it with 400
    if isinstance(resp, dict) and "error" in resp:
        return make_response(jsonify(resp), 400)
    # otherwise it's pure data (list or dict) — jsonify it
    return jsonify(resp)

class Data(Resource):
    def get(self):
        return _maybe_error(get_all_data())

class Customer(Resource):
    def get(self, customer_id):
        return _maybe_error(get_customer_data(customer_id))

class ProductCategory(Resource):
    def get(self, category):
        return _maybe_error(get_product_category_data(category))

class OrderPriority(Resource):
    def get(self, priority):
        return _maybe_error(get_orders_by_priority(priority))

class TotalSalesByCategory(Resource):
    def get(self):
        return _maybe_error(total_sales_by_category())

class HighProfitProducts(Resource):
    def get(self):
        return _maybe_error(high_profit_products())

class ShippingCostSummary(Resource):
    def get(self):
        return jsonify(shipping_cost_summary())

class ProfitByGender(Resource):
    def get(self):
        return _maybe_error(profit_by_gender())

api.add_resource(Data,                   "/data")
api.add_resource(Customer,               "/data/customer/<int:customer_id>")
api.add_resource(ProductCategory,        "/data/product-category/<string:category>")
api.add_resource(OrderPriority,          "/data/order-priority/<string:priority>")
api.add_resource(TotalSalesByCategory,   "/data/total-sales-by-category")
api.add_resource(HighProfitProducts,     "/data/high-profit-products")
api.add_resource(ShippingCostSummary,    "/data/shipping-cost-summary")
api.add_resource(ProfitByGender,         "/data/profit-by-gender")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status":"healthy"})

if __name__=="__main__":
    port = int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0", port=port)
