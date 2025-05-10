from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from flasgger import Swagger
from product_retriever import ProductRetriever
from cachetools import TTLCache
import logging
import os

app = Flask(__name__)
api = Api(app)
swagger = Swagger(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the product retriever
retriever = ProductRetriever()

# Cache for frequently requested queries
cache = TTLCache(maxsize=1000, ttl=300)

class Health(Resource):
    def get(self):
        """
        Health check endpoint.
        ---
        responses:
          200:
            description: Returns a healthy status.
        """
        return jsonify({"status": "healthy"})

class ProductSearch(Resource):
    def post(self):
        """
        Product search endpoint.
        ---
        parameters:
          - name: query
            in: body
            type: string
            required: true
            description: The search query.
          - name: top_k
            in: body
            type: integer
            description: The number of results to return (default: 5).
          - name: min_rating
            in: body
            type: number
            description: The minimum rating for the results (default: 4.0).
        responses:
          200:
            description: Returns a list of products matching the search query.
          400:
            description: Missing query parameter.
        """
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "Missing query parameter"}), 400
        
        try:
            query = data.get('query')
            top_k = data.get('top_k', 5)
            min_rating = data.get('min_rating', 4.0)
            
            cache_key = f"{query}-{top_k}-{min_rating}"
            
            if cache_key in cache:
                logger.info(f"Cache hit for query: {query}")
                return jsonify(cache[cache_key])
            
            logger.info(f"Processing search query: {query}")
            results = retriever.search(
                query=query,
                top_k=top_k,
                min_rating=min_rating
            )
            
            response = []
            for item in results:
                if hasattr(item, "to_dict"):
                    # Product instance
                    response.append(item.to_dict())
                elif isinstance(item, dict):
                    # Already a dict
                    response.append(item)
                else:
                    # Fallback: try its __dict__
                    try:
                        response.append(item.__dict__)
                    except Exception:
                        # As last resort, string‑ify
                        response.append({"value": str(item)})

            return jsonify(response)
        except Exception as e:
            logger.exception("Error during product search")
            return jsonify({"error": "Internal server error"}), 500

class Product(Resource):
    def get(self, asin):
        """
        Get product by ASIN.
        ---
        parameters:
          - name: asin
            in: path
            type: string
            required: true
            description: The ASIN of the product to retrieve.
        responses:
          200:
            description: Returns the product with the given ASIN.
          404:
            description: Product not found.
        """
        product = retriever.get_by_asin(asin)
        if not product:
            return jsonify({"error": "Product not found"}), 404
        try:
            return jsonify(product.to_dict())
        except Exception as e:
            logger.exception("Error during get product")
            return jsonify({"error": "Internal server error"}), 500

api.add_resource(Health, '/health')
api.add_resource(ProductSearch, '/search')
api.add_resource(Product, '/product/<string:asin>')

@app.errorhandler(400)
def bad_request(error):
    """
    Error handler for bad requests.
    ---
    responses:
      400:
        description: Bad request.
    """
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(404)
def not_found(error):
    """
    Error handler for not found errors.
    ---
    responses:
      404:
        description: Resource not found.
    """
    return jsonify({"error": "Resource not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
