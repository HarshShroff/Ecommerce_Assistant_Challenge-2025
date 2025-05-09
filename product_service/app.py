from flask import Flask, jsonify, request
from product_retriever import ProductRetriever
from cachetools import TTLCache
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the product retriever
retriever = ProductRetriever()

# Cache for frequently requested queries
cache = TTLCache(maxsize=1000, ttl=300)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/search', methods=['POST'])
def product_search():
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Missing query parameter"}), 400
        
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

@app.route('/product/<asin>', methods=['GET'])
def get_product(asin):
    product = retriever.get_by_asin(asin)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product.to_dict())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
