import unittest
import requests
import json
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestChatService(unittest.TestCase):
    def setUp(self):
        # Get the chat service URL from environment or use default
        self.base_url = os.environ.get('CHAT_SERVICE_URL', 'https://ecommerce-chat-service-lingering-thunder-5768.fly.dev')
        
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
    
    def test_chat_endpoint_product_query(self):
        """Test if the chat endpoint handles product queries"""
        try:
            payload = {'message': 'Show me microphones under $30'}
            response = requests.post(f"{self.base_url}/chat", json=payload, timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            print(f"✅ Chat endpoint processed product query")
            print(f"Response: {json.dumps(data, indent=2)}")
        except requests.exceptions.RequestException as e:
            self.fail(f"Chat endpoint product query test failed: {str(e)}")
    
    def test_chat_endpoint_order_query(self):
        """Test if the chat endpoint handles order queries"""
        try:
            payload = {'message': 'Check my order with customer ID 37077'}
            response = requests.post(f"{self.base_url}/chat", json=payload, timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            print(f"✅ Chat endpoint processed order query")
            print(f"Response: {json.dumps(data, indent=2)}")
        except requests.exceptions.RequestException as e:
            self.fail(f"Chat endpoint order query test failed: {str(e)}")

if __name__ == '__main__':
    unittest.main()
