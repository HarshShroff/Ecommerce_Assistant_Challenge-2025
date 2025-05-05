import unittest
import requests
import json
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Get service URLs from environment or use defaults
        self.product_url = os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:8000')
        self.order_url = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:8001')
        self.chat_url = os.environ.get('CHAT_SERVICE_URL', 'http://localhost:8002')
    
    def test_end_to_end_product_flow(self):
        """Test the complete flow from chat to product service"""
        try:
            # First, check if all services are healthy
            self._check_health(self.product_url)
            self._check_health(self.chat_url)
            
            # Send a product query to the chat service
            chat_payload = {'message': 'Show me top rated guitar strings'}
            chat_response = requests.post(f"{self.chat_url}/chat", json=chat_payload, timeout=10)
            self.assertEqual(chat_response.status_code, 200)
            chat_data = chat_response.json()
            
            # Verify the chat response contains product information
            self.assertIn('response', chat_data)
            product_response = chat_data['response']
            
            # Now directly query the product service
            product_payload = {'query': 'guitar strings', 'top_k': 3}
            product_response = requests.post(f"{self.product_url}/search", json=product_payload, timeout=10)
            self.assertEqual(product_response.status_code, 200)
            product_data = product_response.json()
            
            # Verify that the products returned directly match what's in the chat response
            # This is a loose check since the chat formats the response
            if product_data:
                product_title = product_data[0]['title'].lower()
                self.assertTrue(product_title in chat_data['response'].lower())
            
            print("✅ End-to-end product flow test passed")
        except requests.exceptions.RequestException as e:
            self.fail(f"End-to-end product flow test failed: {str(e)}")
    
    def test_end_to_end_order_flow(self):
        """Test the complete flow from chat to order service"""
        try:
            # First, check if all services are healthy
            self._check_health(self.order_url)
            self._check_health(self.chat_url)
            
            # Send an order query to the chat service
            customer_id = "37077"
            chat_payload = {'message': f'Check my order with customer ID {customer_id}'}
            chat_response = requests.post(f"{self.chat_url}/chat", json=chat_payload, timeout=10)
            self.assertEqual(chat_response.status_code, 200)
            chat_data = chat_response.json()
            
            # Verify the chat response contains order information
            self.assertIn('response', chat_data)
            
            # Now directly query the order service
            order_response = requests.get(f"{self.order_url}/orders/{customer_id}", timeout=10)
            self.assertEqual(order_response.status_code, 200)
            order_data = order_response.json()
            
            # Verify that order details match what's in the chat response
            if order_data and 'orders' in order_data and order_data['orders']:
                order = order_data['orders'][0]
                # Check if product name from order appears in chat response
                product_name = order['Product']
                self.assertTrue(product_name in chat_data['response'])
            
            print("✅ End-to-end order flow test passed")
        except requests.exceptions.RequestException as e:
            self.fail(f"End-to-end order flow test failed: {str(e)}")
    
    def _check_health(self, service_url):
        """Helper to check if a service is healthy"""
        response = requests.get(f"{service_url}/health", timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')

if __name__ == '__main__':
    unittest.main()
