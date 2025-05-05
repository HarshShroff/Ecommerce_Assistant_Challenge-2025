import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self):
        self.product_templates = {
            "no_results": "I couldn't find any products matching your query. Could you try with different keywords?",
            "single_result": "I found a great product that might interest you: {title}. It's priced at ${price} and has a rating of {rating}/5 stars. {features}",
            "multiple_results": "Here are some products that match your search:\n\n{products}\n\nWould you like more details about any of these products?"
        }
        
        self.order_templates = {
            "no_orders": "I couldn't find any orders for customer ID {customer_id}.",
            "single_order": "Your most recent order was placed on {date} for '{product}'. The total amount was ${sales}, with a shipping cost of ${shipping}. The order priority is marked as '{priority}'.",
            "multiple_orders": "You have {count} orders. Your most recent order was placed on {date} for '{product}'. The total amount was ${sales}, with a shipping cost of ${shipping}. Would you like to see details of your other orders?"
        }
    
    def generate_product_response(self, products, query):
        """Generate a response for product queries using the retrieved products"""
        if not products:
            return self.product_templates["no_results"]
                
        if len(products) == 1:
            product = products[0]
            features = ""
            if product.get('features') and len(product['features']) > 0:
                features = f"Some key features include: {'; '.join(product['features'][:2])}"
                    
            return self.product_templates["single_result"].format(
                title=product['title'],
                price=product['price'],
                rating=product['rating'],
                features=features
            )
        
        # Format multiple products
        product_list = []
        for i, product in enumerate(products[:5], 1):
            product_list.append(f"{i}. {product['title']} - ${product['price']} (Rating: {product['rating']}/5)")
        
        # Add price analysis
        prices = [float(p['price']) for p in products]
        avg_price = sum(prices) / len(prices)
        price_analysis = f"\nThe average price of these products is ${avg_price:.2f}."
        
        return self.product_templates["multiple_results"].format(
            products="\n".join(product_list)
        ) + price_analysis

    
    def generate_order_response(self, order_data, query):
        """Generate a response for order queries using the retrieved order data"""
        customer_id = order_data.get('customer_id')
        orders = order_data.get('orders', [])
        
        if not orders:
            return self.order_templates["no_orders"].format(customer_id=customer_id)
        
        # Sort orders by date (most recent first)
        orders.sort(key=lambda x: x.get('Order_Date', ''), reverse=True)
        most_recent = orders[0]
        
        # Format date
        date_str = most_recent.get('Order_Date', '')
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
        except:
            formatted_date = date_str
        
        if len(orders) == 1:
            return self.order_templates["single_order"].format(
                date=formatted_date,
                product=most_recent.get('Product', 'Unknown product'),
                sales=most_recent.get('Sales', 0),
                shipping=most_recent.get('Shipping_Cost', 0),
                priority=most_recent.get('Order_Priority', 'Standard')
            )
        
        # For multiple orders
        return self.order_templates["multiple_orders"].format(
            count=len(orders),
            date=formatted_date,
            product=most_recent.get('Product', 'Unknown product'),
            sales=most_recent.get('Sales', 0),
            shipping=most_recent.get('Shipping_Cost', 0),
            priority=most_recent.get('Order_Priority', 'Standard')
        )
