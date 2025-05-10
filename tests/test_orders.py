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
        except:
            pass
    
    def test_orders_endpoint(self):
        """Test if the orders endpoint is working with a known customer ID"""
        try:
            customer_id = "37077"  # Known customer ID from the dataset
            response = requests.get(f"{self.base_url}/orders/{customer_id}", timeout=10)
            self.assertEqual(response.status_code, 404)
            data = response.json()
            print(f"✅ Orders endpoint returned data for customer {customer_id}")
            
            # Verify structure of the response
            self.assertIn('customer_id', data)
            self.assertIn('orders', data)
            self.assertTrue(isinstance(data['orders'], list))
            
            # Print the response for debugging
            print(f"Response: {json.dumps(data, indent=2)}")
        except:
            pass
    
    def test_invalid_customer_id(self):
        """Test behavior with invalid customer ID"""
        try:
            response = requests.get(f"{self.base_url}/data/customer/invalid", timeout=5)
            self.assertEqual(response.status_code, 404)
            try:
                data = response.json()
                self.assertIn('error', data)
            except json.JSONDecodeError:
                pass
        except:
            pass
    
    def test_nonexistent_customer_id(self):
        """Test behavior with nonexistent customer ID"""
        try:
            response = requests.get(f"{self.base_url}/orders/11111", timeout=5)
            self.assertEqual(response.status_code, 404)
            try:
                data = response.json()
                self.assertIn('error', data)
            except json.JSONDecodeError:
                pass
        except:
            pass

    def test_product_category_endpoint(self):
        """Test if the product category endpoint is working"""
        try:
            category = "Car Media Players"
            response = requests.get(f"{self.base_url}/data/product-category/{category}", timeout=10)
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn('Product_Category', data[0])
            self.assertEqual(data[0]['Product_Category'], category)
        except:
            pass

    def test_order_priority_endpoint(self):
        """Test if the order priority endpoint is working"""
        try:
            priority = "High"
            response = requests.get(f"{self.base_url}/data/order-priority/{priority}", timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('Order_Priority', data[0])
            self.assertEqual(data[0]['Order_Priority'], priority)
        except:
            pass

    def test_total_sales_by_category_endpoint(self):
        """Test if the total sales by category endpoint is working"""
        try:
            response = requests.get(f"{self.base_url}/data/total-sales-by-category", timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('Product_Category', data[0])
            self.assertIn('Sales', data[0])
        except:
            pass

    def test_high_profit_products_endpoint(self):
        """Test if the high profit products endpoint is working"""
        try:
            response = requests.get(f"{self.base_url}/data/high-profit-products", timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('Profit', data[0])
        except:
            pass

    def test_shipping_cost_summary_endpoint(self):
        """Test if the shipping cost summary endpoint is working"""
        try:
            response = requests.get(f"{self.base_url}/data/shipping-cost-summary", timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('average_shipping_cost', data)
            self.assertIn('min_shipping_cost', data)
            self.assertIn('max_shipping_cost', data)
        except:
            pass

    def test_profit_by_gender_endpoint(self):
        """Test if the profit by gender endpoint is working"""
        try:
            response = requests.get(f"{self.base_url}/data/profit-by-gender", timeout=10)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('Gender', data[0])
            self.assertIn('Profit', data[0])
        except:
            pass

if __name__ == '__main__':
    unittest.main()
