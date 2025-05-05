import unittest
import requests
import json
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestOrderService(unittest.TestCase):
    def setUp(self):
        # Get the order service URL from environment or use default
        self.base_url = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:8001')
        
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
    
    def test_orders_endpoint(self):
        """Test if the orders endpoint is working with a known customer ID"""
        try:
            customer_id = "37077"  # Known customer ID from the dataset
            response = requests.get(f"{self.base_url}/orders/{customer_id}", timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            print(f"✅ Orders endpoint returned data for customer {customer_id}")
            
            # Verify structure of the response
            self.assertIn('customer_id', data)
            self.assertIn('orders', data)
            self.assertTrue(isinstance(data['orders'], list))
            
            # Print the response for debugging
            print(f"Response: {json.dumps(data, indent=2)}")
        except requests.exceptions.RequestException as e:
            self.fail(f"Orders endpoint test failed: {str(e)}")
    
    def test_invalid_customer_id(self):
        """Test behavior with invalid customer ID"""
        try:
            response = requests.get(f"{self.base_url}/orders/invalid", timeout=5)
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIn('error', data)
        except requests.exceptions.RequestException as e:
            self.fail(f"Invalid customer ID test failed: {str(e)}")
    
    def test_nonexistent_customer_id(self):
        """Test behavior with nonexistent customer ID"""
        try:
            response = requests.get(f"{self.base_url}/orders/11111", timeout=5)
            self.assertEqual(response.status_code, 404)
            data = response.json()
            self.assertIn('error', data)
        except (requests.exceptions.RequestException, requests.exceptions.ReadTimeout) as e:
            self.fail(f"Nonexistent customer ID test failed: {str(e)}")

if __name__ == '__main__':
    unittest.main()
