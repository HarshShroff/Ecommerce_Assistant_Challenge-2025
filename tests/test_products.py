import unittest
import requests
import json
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestProductService(unittest.TestCase):
    def setUp(self):
        # Get the product service URL from environment or use default
        self.base_url = os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:8000')
        
    def test_health_endpoint(self):
        """Test if the health endpoint is responding"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'healthy')
            print("✅ Health check passed")
        except requests.exceptions.RequestException as e:
            self.fail(f"Health check failed: {str(e)}")
    
    def test_search_endpoint(self):
        """Test if the search endpoint is working"""
        try:
            payload = {'query': 'microphone', 'top_k': 3}
            response = requests.post(f"{self.base_url}/search", json=payload, timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            print(f"✅ Search endpoint returned {len(data)} results")
            
            # Print the first result for debugging
            if data:
                print(f"Sample result: {json.dumps(data[0], indent=2)}")
                
            # Verify the structure of returned products
            if data:
                product = data[0]
                self.assertIn('asin', product)
                self.assertIn('title', product)
                self.assertIn('price', product)
                self.assertIn('rating', product)
        except requests.exceptions.RequestException as e:
            self.fail(f"Search endpoint test failed: {str(e)}")
    
    def test_search_with_filters(self):
        """Test search with rating filter"""
        try:
            payload = {'query': 'guitar', 'top_k': 3, 'min_rating': 4.5}
            response = requests.post(f"{self.base_url}/search", json=payload, timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            
            # Verify all returned products have rating >= 4.5
            for product in data:
                self.assertGreaterEqual(product['rating'], 4.5)
        except requests.exceptions.RequestException as e:
            self.fail(f"Search with filters test failed: {str(e)}")
    
    def test_hybrid_search(self):
        """Test if the hybrid search is working"""
        try:
            payload = {'query': 'guitar strings', 'top_k': 3}
            response = requests.post(f"{self.base_url}/search", json=payload, timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            print(f"✅ Hybrid search endpoint returned {len(data)} results")
            
            # Verify that the results contain "guitar strings"
            for product in data:
                self.assertIn("guitar strings", product['title'].lower())
        except requests.exceptions.RequestException as e:
            self.fail(f"Hybrid search test failed: {str(e)}")

if __name__ == '__main__':
    unittest.main()
