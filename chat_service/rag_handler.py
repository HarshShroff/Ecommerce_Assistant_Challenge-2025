# chat_service/rag_handler.py
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self):
        self.analytics_templates = {
            "sales_by_category": "Here’s the total sales by category:\n\n{lines}",
            "profit_by_gender":   "Total profit by customer gender:\n\n{lines}",
            "shipping_summary":   "Shipping cost summary:\n\nAverage: ${average:.2f}\nMin: ${min:.2f}\nMax: ${max:.2f}",
            "high_profit":        "Here are high-profit products:\n\n{lines}"
        }
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

    # ──────────────────────────────────────────────────────────────────────────────
    # Analytics responses
    # ──────────────────────────────────────────────────────────────────────────────

    def generate_sales_by_category(self, data):
        header = "Here’s the total sales by category:"
        lines = []
        for d in data:
            cat = d.get('Product_Category', 'Unknown')
            sales = d.get('Sales', 0.0)
            lines.append(f"- {cat}: ${sales:.2f}")
        return "\n".join([header] + lines)

    def generate_profit_by_gender(self, data):
        header = "Total profit by customer gender:"
        lines = []
        for d in data:
            gender = d.get('Gender', 'Unknown')
            profit = d.get('Profit', 0.0)
            lines.append(f"- {gender}: ${profit:.2f}")
        return "\n".join([header] + lines)

    def generate_shipping_summary(self, summary):
        return (
            "Shipping cost summary:\n"
            f"- Average: ${summary['average_shipping_cost']:.2f}\n"
            f"- Minimum: ${summary['min_shipping_cost']:.2f}\n"
            f"- Maximum: ${summary['max_shipping_cost']:.2f}"
        )

    def generate_high_profit_products(self, data):
        header = "Here are some high‑profit products:"
        lines = []
        for i, d in enumerate(data[:5], start=1):
            name = d.get('Product') or d.get('Product_Category', 'Unknown')
            profit = d.get('Profit', 0.0)
            lines.append(f"{i}. {name} — Profit: ${profit:.2f}")
        return "\n".join([header] + lines)

    # ──────────────────────────────────────────────────────────────────────────────
    # Product search response
    # ──────────────────────────────────────────────────────────────────────────────

    def generate_product_response(self, products, query):
        if not products:
            return "I couldn't find any products matching your query. Could you try different keywords?"

        if len(products) == 1:
            p = products[0]
            title = p.get('title', 'N/A')
            price = p.get('price', 0.0)
            rating = p.get('rating', 0.0)
            feat = p.get('features') or []
            feat_txt = ""
            if feat:
                feat_txt = " Key features: " + "; ".join(feat[:3]) + "."
            return (
                f"I found one product for '{query}': {title} priced at "
                f"${price:.2f} with a {rating:.1f}/5 star rating.{feat_txt}"
            )

        header = f"Here are the top {min(len(products), 5)} results for '{query}':"
        lines = []
        prices = []
        for i, p in enumerate(products[:5], start=1):
            title = p.get('title', 'N/A')
            price = p.get('price')
            try:
                price_f = float(price)
                prices.append(price_f)
                price_str = f"${price_f:.2f}"
            except Exception:
                price_str = "N/A"
            rating = p.get('rating', 0.0)
            lines.append(f"{i}. {title} — {price_str} (Rating: {rating:.1f}/5)")

        price_summary = ""
        if prices:
            avg = sum(prices) / len(prices)
            price_summary = f"\nThe average price of these is ${avg:.2f}."

        return "\n".join([header] + lines) + price_summary

    # ──────────────────────────────────────────────────────────────────────────────
    # General order response
    # ──────────────────────────────────────────────────────────────────────────────

    def generate_order_response(self, order_data, query):
        cid = order_data.get('customer_id', 'Unknown')
        orders = order_data.get('orders', [])
        if not orders:
            return f"I couldn't find any orders for Customer ID {cid}."

        try:
            orders_sorted = sorted(
                orders,
                key=lambda o: datetime.strptime(o.get('Order_Date', ''), '%Y-%m-%d'),
                reverse=True
            )
        except Exception:
            orders_sorted = orders

        most_recent = orders_sorted[0]
        date_str = most_recent.get('Order_Date', '')
        try:
            date_fmt = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
        except Exception:
            date_fmt = date_str

        product = most_recent.get('Product') or most_recent.get('Product_Category', 'Unknown')
        sales = most_recent.get('Sales', 0.0)
        shipping = most_recent.get('Shipping_Cost', 0.0)
        priority = most_recent.get('Order_Priority', 'N/A')

        if len(orders_sorted) == 1:
            return (
                f"Your only order (Customer ID {cid}) was on {date_fmt}: "
                f"{product} for ${sales:.2f} (shipping ${shipping:.2f}), priority: {priority}."
            )

        return (
            f"You have {len(orders_sorted)} orders. Your most recent was on {date_fmt}: "
            f"{product} for ${sales:.2f} (shipping ${shipping:.2f}), priority: {priority}. "
            "Let me know if you'd like details on any other order!"
        )

    # ──────────────────────────────────────────────────────────────────────────────
    # Priority‑orders response
    # ──────────────────────────────────────────────────────────────────────────────

    def generate_priority_orders_response(self, orders, priority_level):
        if not orders:
            return f"I couldn't find any {priority_level.lower()}‑priority orders."

        header = f"Here are the {len(orders)} most recent {priority_level.lower()}‑priority orders:"
        lines = []
        for i, o in enumerate(orders, start=1):
            date_str = o.get('Order_Date', '')
            try:
                date_fmt = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
            except Exception:
                date_fmt = date_str

            product = o.get('Product') or o.get('Product_Category', 'Unknown')
            sales = o.get('Sales', 0.0)
            shipping = o.get('Shipping_Cost', 0.0)
            cid = o.get('Customer_Id', 'N/A')

            lines.append(
                f"{i}. {date_fmt} — {product} for ${sales:.2f} "
                f"(shipping ${shipping:.2f}; Customer ID: {cid})"
            )

        return "\n".join([header] + lines)
