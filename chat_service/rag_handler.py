import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatHandler:
    """
    Handles chat-related logic, including generating responses for product and order queries.
    """
    def __init__(self):
        """
        Initializes the ChatHandler with templates for product and order responses.
        """
        self.product_templates = {
            "no_results": "I couldn't find any products matching your query. Could you try with different keywords?",
            "single_result": "I found this product for you: {title}. It's priced at ${price} and has a rating of {rating}/5 stars. {features}",
            "multiple_results": "Here are some products that match your search:\n\n{products}\n\nWould you like more details on any of these?"
        }
        self.order_templates = {
            "no_orders": "I couldn't find any orders for customer ID {customer_id}.",
            "single_order": "Your most recent order was placed on {date} for '{product}'. The total amount was ${sales:.2f}, with a shipping cost of ${shipping:.2f}. The order priority is '{priority}'.",
            "multiple_orders": "You have {count} orders. Your most recent order was placed on {date} for '{product}'. The total amount was ${sales:.2f}, with a shipping cost of ${shipping:.2f}. Want details on other orders?"
        }

    def generate_product_response(self, products, query):
        """
        Generates a response for product queries.

        Args:
            products (list): A list of products matching the query.
            query (str): The original user query.

        Returns:
            str: A formatted response string.
        """
        if not products:
            return self.product_templates["no_results"]

        if len(products) == 1:
            product = products[0]
            features_text = ""
            if product.get('features') and isinstance(product['features'], list) and len(product['features']) > 0:
                features_text = f"Key features: {'; '.join(product['features'][:2])}."
            return self.product_templates["single_result"].format(
                title=product.get('title', 'N/A'),
                price=product.get('price', 0.0),
                rating=product.get('rating', 0.0),
                features=features_text
            )

        product_list_str = []
        valid_prices = []
        for i, product in enumerate(products[:5], 1):
            price = product.get('price')
            if price is not None:
                try:
                    price_float = float(price)
                    valid_prices.append(price_float)
                    price_str = f"${price_float:.2f}"
                except (ValueError, TypeError):
                    price_str = "$N/A"
            else:
                price_str = "$N/A"

            product_list_str.append(
                f"{i}. {product.get('title', 'N/A')} - {price_str} (Rating: {product.get('rating', 0.0):.1f}/5)"
            )

        price_analysis = ""
        if valid_prices:
            avg_price = sum(valid_prices) / len(valid_prices)
            price_analysis = f"\nThe average price of these products is ${avg_price:.2f}."

        enhanced_info = ""
        if hasattr(self, 'perplexity') and self.perplexity.api_key:
            try:
                enhanced_query = f"Provide brief market insights for {query} products, including trends and typical price ranges, in about 2-3 sentences."
                perplexity_result = self.perplexity.search(enhanced_query)
                if "content" in perplexity_result:
                    enhanced_info = f"\n\n**Market Insights**: {perplexity_result['content']}"
            except Exception as e:
                logger.error(f"Error fetching Perplexity insights: {e}")

        return self.product_templates["multiple_results"].format(
            products="\n".join(product_list_str)
        ) + price_analysis + enhanced_info

    def generate_order_response(self, order_data, query):
        """
        Generates a response for order queries.

        Args:
            order_data (dict): A dictionary containing order information.
            query (str): The original user query.

        Returns:
            str: A formatted response string.
        """
        customer_id = order_data.get('customer_id')
        orders = order_data.get('orders', [])

        if not orders:
            return self.order_templates["no_orders"].format(customer_id=customer_id)

        most_recent_order = orders[0]

        date_str = most_recent_order.get('Order_Date', '')
        formatted_date = date_str
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date: {date_str}")

        sales_val = most_recent_order.get('Sales', 0.0)
        shipping_val = most_recent_order.get('Shipping_Cost', 0.0)

        if len(orders) == 1:
            return self.order_templates["single_order"].format(
                date=formatted_date,
                product=most_recent_order.get('Product', 'N/A'),
                sales=float(sales_val),
                shipping=float(shipping_val),
                priority=most_recent_order.get('Order_Priority', 'N/A')
            )
        else:
            return self.order_templates["multiple_orders"].format(
                count=len(orders),
                date=formatted_date,
                product=most_recent_order.get('Product', 'N/A'),
                sales=float(sales_val),
                shipping=float(shipping_val),
                priority=most_recent_order.get('Order_Priority', 'N/A')
            )

    def generate_priority_orders_response(self, orders: list[dict[str, any]], priority_level: str) -> str:
        """
        Generates a formatted response for a list of priority orders.

        Args:
            orders (list[dict[str, any]]): A list of priority orders.
            priority_level (str): The priority level of the orders.

        Returns:
            str: A formatted response string.
        """
        if not orders:
            return f"I couldn't find any {priority_level.lower()} priority orders at the moment."

        response_lines = [
            f"Here are the {len(orders)} most recent {priority_level.lower()}-priority orders I found:"]

        for i, order_item in enumerate(orders, 1):
            date_str = order_item.get('Order_Date', '')
            formatted_date = date_str
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%B %d, %Y')
            except (ValueError, TypeError):
                logger.warning(
                    f"Could not parse date for priority order: {date_str}")

            product_name = order_item.get('Product', 'N/A')
            sales_val = order_item.get('Sales', 0.0)
            shipping_val = order_item.get('Shipping_Cost', 0.0)
            cust_id = order_item.get('Customer_Id', 'N/A')

            response_lines.append(
                f"{i}. On {formatted_date}, {product_name} was ordered for ${float(sales_val):.2f} "
                f"with a shipping cost of ${float(shipping_val):.2f}. (Customer ID: {cust_id})."
            )

        response_lines.append(
            "\nLet me know if you'd like more details about any of these orders!")
        return "\n".join(response_lines)
