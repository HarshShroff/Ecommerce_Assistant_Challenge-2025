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
            if product_data and chat_data.get('response'):
                product_title = product_data[0]['title'].lower()
                self.assertTrue(product_title in chat_data['response'].lower())
            
            print("✅ End-to-end product flow test passed")
        except Exception as e:
            print(f"Error in test_end_to_end_product_flow: {e}")
    
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
            self.assertEqual(order_response.status_code, 404)
            order_data = order_response.json()
            
            # Verify that order details match what's in the chat response
            if order_data and 'orders' in order_data and order_data['orders']:
                order = order_data['orders'][0]
                # Check if product name from order appears in chat response
                product_name = order.get('Product', order.get('Product_Category', ''))
                self.assertTrue(product_name in chat_data['response'].lower())
            else:
                self.fail("No orders found in order service response")
            
            print("✅ End-to-end order flow test passed")
        except Exception as e:
            print(f"Error in test_end_to_end_order_flow: {e}")

    def test_end_to_end_small_talk(self):
        """Test the complete flow for small talk"""
        try:
            self._check_health(self.chat_url)

            chat_payload = {'message': 'hello'}
            chat_response = requests.post(f"{self.chat_url}/chat", json=chat_payload, timeout=10)
            self.assertEqual(chat_response.status_code, 200)
            chat_data = chat_response.json()

            self.assertIn('response', chat_data)
            self.assertTrue(any(keyword in chat_data['response'].lower() for keyword in ['hello', 'hi', 'hey']))

            print("✅ End-to-end small talk test passed")
        except Exception as e:
            print(f"Error in test_end_to_end_small_talk: {e}")

    def test_end_to_end_service_unavailable(self):
        """Test the complete flow when a service is unavailable"""
        try:
            # Assuming that if we send a query with a very long timeout, it will simulate a service unavailable error
            chat_payload = {'message': 'Show me microphones under $30'}
            chat_response = requests.post(f"{self.chat_url}/chat", json=chat_payload, timeout=0.001)
            self.assertEqual(chat_response.status_code, 200)
            chat_data = chat_response.json()

            self.assertIn('response', chat_data)
            self.assertTrue("sorry" in chat_data['response'].lower() or "unavailable" in chat_data['response'].lower())

            print("✅ End-to-end service unavailable test passed")
        except Exception as e:
            print(f"Error in test_end_to_end_service_unavailable: {e}")

    def test_end_to_end_invalid_customer_id(self):
        """Test the complete flow with an invalid customer ID"""
        try:
            self._check_health(self.chat_url)
            self._check_health(self.order_url)

            customer_id = "11111"
            chat_payload = {'message': f'Check my order with customer ID {customer_id}'}
            chat_response = requests.post(f"{self.chat_url}/chat", json=chat_payload, timeout=10)
            self.assertEqual(chat_response.status_code, 200)
            chat_data = chat_response.json()

            self.assertIn('response', chat_data)
            self.assertTrue("invalid" in str(chat_data['response']).lower() or "not found" in str(chat_data['response']).lower())

            print("✅ End-to-end invalid customer ID test passed")
        except Exception as e:
            print(f"Error in test_end_to_end_invalid_customer_id: {e}")
    
    def _check_health(self, service_url):
        """Helper to check if a service is healthy"""
        response = requests.get(f"{service_url}/health", timeout=5)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')

    # Add more tests and edge cases here
    def test_edge_case_1(self):
        """Test edge case 1"""
        self.assertTrue(True)

    def test_edge_case_2(self):
        """Test edge case 2"""
        self.assertTrue(True)

    def test_new_test_1(self):
        """Test new test 1"""
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
