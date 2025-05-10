import os
import sys

# ensure project root (where mock_api/ lives) is on PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, jsonify
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
    if isinstance(resp, dict) and "error" in resp:
        return jsonify(resp), 404
    return jsonify(resp)

class Data(Resource):
    def get(self):
        """
        Retrieve all records in the dataset.
        ---
        responses:
          200:
            description: All records in the dataset
        """
        return _maybe_error(get_all_data())

class Customer(Resource):
    def get(self, customer_id):
        """
        Retrieve all records for a specific Customer ID.
        ---
        parameters:
          - name: customer_id
            in: path
            type: integer
            required: true
            description: ID of the customer to retrieve
        responses:
          200:
            description: All records for a specific Customer ID
          404:
            description: No data found for the Customer ID
        """
        return _maybe_error(get_customer_data(customer_id))

class ProductCategory(Resource):
    def get(self, category):
        """
        Retrieve all records for a specific Product Category.
        ---
        parameters:
          - name: category
            in: path
            type: string
            required: true
            description: Category of the product to retrieve
        responses:
          200:
            description: All records for a specific Product Category
          404:
            description: No data found for the Product Category
        """
        return _maybe_error(get_product_category_data(category))

class OrderPriority(Resource):
    def get(self, priority):
        """
        Retrieve all orders with the given priority.
        ---
        parameters:
          - name: priority
            in: path
            type: string
            required: true
            description: Priority of the order to retrieve
        responses:
          200:
            description: All orders with the given priority
          404:
            description: No data found for the Order Priority
        """
        return _maybe_error(get_orders_by_priority(priority))

class TotalSalesByCategory(Resource):
    def get(self):
        """
        Calculate total sales by Product Category.
        ---
        responses:
          200:
            description: Total sales by Product Category
        """
        return _maybe_error(total_sales_by_category())

class HighProfitProducts(Resource):
    def get(self):
        """
        Retrieve products with profit greater than the specified value.
        ---
        responses:
          200:
            description: Products with profit greater than the specified value
          404:
            description: No products found with profit greater than the specified value
        """
        return _maybe_error(high_profit_products())

class ShippingCostSummary(Resource):
    def get(self):
        """
        Retrieve the average, minimum, and maximum shipping cost.
        ---
        responses:
          200:
            description: The average, minimum, and maximum shipping cost
        """
        return jsonify(shipping_cost_summary())

class ProfitByGender(Resource):
    def get(self):
        """
        Calculate total profit by customer gender.
        ---
        responses:
          200:
            description: Total profit by customer gender
        """
        return _maybe_error(profit_by_gender())

api.add_resource(Data, "/data")
api.add_resource(Customer, "/data/customer/<int:customer_id>")
api.add_resource(ProductCategory, "/data/product-category/<string:category>")
api.add_resource(OrderPriority, "/data/order-priority/<string:priority>")
api.add_resource(TotalSalesByCategory, "/data/total-sales-by-category")
api.add_resource(HighProfitProducts, "/data/high-profit-products")
api.add_resource(ShippingCostSummary, "/data/shipping-cost-summary")
api.add_resource(ProfitByGender, "/data/profit-by-gender")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
