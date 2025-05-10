import logging
import re
from datetime import datetime

from perplexity_client import PerplexityClient

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self, perplexity_api_key=None):
        # Always set attribute, even if None
        self.perplexity = None
        if perplexity_api_key:
            try:
                self.perplexity = PerplexityClient(api_key=perplexity_api_key)
            except Exception as e:
                logger.error(f"Failed to initialize PerplexityClient: {e}")

        # Analytics response templates
        self.analytics_templates = {
            "sales_by_category": "Here’s the total sales by category:\n\n{lines}",
            "profit_by_gender":   "Total profit by customer gender:\n\n{lines}",
            "shipping_summary": ("Shipping cost summary:\n\n"
                                 "Average: ${average:.2f}\n"
                                 "Min: ${min:.2f}\n"
                                 "Max: ${max:.2f}"),
            "high_profit":        "Here are the high-profit products:\n\n{lines}"
        }

        # Order templates
        self.order_templates = {
            "no_orders":      "I couldn't find any orders under Customer ID {customer_id}.",
            "single_order": (
                "Here’s what I found for your most recent order:\n"
                "• Date: {date}\n"
                "• Item: {product}\n"
                "• Total: ${sales:.2f} (Shipping: ${shipping:.2f})\n"
                "Is there anything else you’d like to know?"
            ),
            "multiple_orders": (
                "You have {count} orders. Most recent:\n"
                "• Date: {date}\n"
                "• Item: {product}\n"
                "• Total: ${sales:.2f} (Shipping: ${shipping:.2f})\n"
                "Would you like details on the others?"
            )
        }

    def generate_sales_by_category(self, data):
        lines = "\n".join(f"{d['Product_Category']}: ${d['Sales']:.2f}" for d in data)
        return self.analytics_templates["sales_by_category"].format(lines=lines)

    def generate_profit_by_gender(self, data):
        lines = "\n".join(f"{d['Gender']}: ${d['Profit']:.2f}" for d in data)
        return self.analytics_templates["profit_by_gender"].format(lines=lines)

    def generate_shipping_summary(self, summary):
        return self.analytics_templates["shipping_summary"].format(
            average=summary["average_shipping_cost"],
            min=summary["min_shipping_cost"],
            max=summary["max_shipping_cost"]
        )

    def generate_high_profit_products(self, data):
        lines = []
        for i, d in enumerate(data[:5], start=1):
            lines.append(f"{i}. {d.get('Product') or d.get('Product_Category')} — Profit: ${d['Profit']:.2f}")
        return self.analytics_templates["high_profit"].format(lines="\n".join(lines))

    def generate_product_response(self, products, query):
        # Evaluate "Is X good for Y?" queries
        eval_match = re.match(
            r"is (?:the )?(?P<product>.+?) good for (?P<target>.+?)(?:\?|$)",
            query, flags=re.IGNORECASE
        )
        if eval_match and products:
            prod = products[0]
            target = eval_match.group('target').strip()
            # Prepare prompt for Perplexity
            desc = prod.get('description','')
            feats = prod.get('features', [])
            feat_text = '; '.join(feats[:3]) if feats else ''
            prompt = (
                f"Product: {prod.get('title')}\n"
                f"Description: {desc}\n"
                f"Key Features: {feat_text}\n"
                f"Question: Is this product good for {target}? Explain briefly."
            )
            if self.perplexity:
                try:
                    insight = self.perplexity.search(prompt).get('content')
                    if insight:
                        return insight
                except Exception as e:
                    logger.error(f"Perplexity evaluation error: {e}")
            # Fallback
            return (
                f"I don’t have a detailed evaluation right now, but here’s the product info:\n"
                f"• {prod.get('title')} — ${prod.get('price',0):.2f}, Rating: {prod.get('rating',0):.1f}/5"
            )

        # Standard search results
        if not products:
            return "I couldn’t find any products matching that. Could you try different keywords?"

        # Single product response
        if len(products) == 1:
            p = products[0]
            feats = p.get('features', [])
            feat_text = ' '.join(feats[:2]) if feats else ''
            return (
                f"Here’s one result: {p.get('title')} for ${p.get('price',0):.2f} "
                f"(Rating: {p.get('rating',0):.1f}/5). {feat_text}"
            )

        # Multiple products
        lines = []
        for i, p in enumerate(products[:5], start=1):
            lines.append(
                f"{i}. {p.get('title')} — ${p.get('price',0):.2f} (Rating: {p.get('rating',0):.1f}/5)"
            )
        resp = "Here are some products that match your search:\n\n" + "\n".join(lines)
        # Optional market insight
        if self.perplexity:
            try:
                insight = self._market_insights(query)
                if insight:
                    resp += f"\n\nMarket Insights: {insight}"
            except Exception:
                pass
        return resp

    def _market_insights(self, query):
        prompt = (
            f"Provide a brief market overview for products matching '{query}', "
            "including trends and price ranges in two sentences."
        )
        return self.perplexity.search(prompt).get('content','') if self.perplexity else ''

    def generate_order_response(self, order_data, query):
        cid = order_data.get('customer_id')
        orders = order_data.get('orders', [])
        if not orders:
            return f"I couldn't find any orders under Customer ID {cid}."

        most_recent = orders[0]
        try:
            dt = datetime.strptime(most_recent['Order_Date'], '%Y-%m-%d')
            date_str = dt.strftime('%B %d, %Y')
        except:
            date_str = most_recent['Order_Date']
        sales = float(most_recent.get('Sales',0))
        ship  = float(most_recent.get('Shipping_Cost',0))
        prod  = most_recent.get('Product','item')

        if len(orders) == 1:
            return (
                f"Here’s what I found for your most recent order:\n"
                f"• Date: {date_str}\n"
                f"• Item: {prod}\n"
                f"• Total: ${sales:.2f} (Shipping: ${ship:.2f})\n"
                f"Is there anything else you’d like to know?"
            )
        return (
            f"You have {len(orders)} orders. Most recent:\n"
            f"• Date: {date_str}\n"
            f"• Item: {prod}\n"
            f"• Total: ${sales:.2f} (Shipping: ${ship:.2f})\n"
            f"Would you like details on the others?"
        )

    def generate_priority_orders_response(self, orders, priority_level):
        if not orders:
            return f"I couldn't find any {priority_level.lower()}-priority orders right now."
        lines = [f"Here are the {len(orders)} most recent {priority_level.lower()}-priority orders:"]
        for i, o in enumerate(orders[:5], start=1):
            try:
                d = datetime.strptime(o['Order_Date'],'%Y-%m-%d').strftime('%B %d, %Y')
            except:
                d = o['Order_Date']
            prod = o.get('Product') or o.get('Product_Category')
            sales = float(o.get('Sales',0))
            ship  = float(o.get('Shipping_Cost',0))
            cid   = o.get('Customer_Id','N/A')
            lines.append(
                f"{i}. On {d}, {prod} for ${sales:.2f} plus ${ship:.2f} shipping. (Customer ID: {cid})"
            )
        lines.append("\nLet me know if you'd like more details!")
        return "\n".join(lines)
