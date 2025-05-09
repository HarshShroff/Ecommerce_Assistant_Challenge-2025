# chat_service/app.py

import os
import re
import uuid
import logging
import requests
from datetime import datetime

from flask import Flask, request, jsonify, render_template
from rag_handler import ChatHandler
from session_manager import SessionManager, Session

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", str(uuid.uuid4()))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

chat_handler    = ChatHandler()
session_manager = SessionManager(session_expiry_seconds=1800)
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8080")
ORDER_SERVICE_URL   = os.getenv("ORDER_SERVICE_URL",   "http://order-service:8080")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})


@app.route("/chat", methods=["POST"])
def handle_chat():
    data = request.get_json(force=True)
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    sid     = data.get("session_id")
    session: Session = session_manager.get_session(sid)
    session.add_to_history("user", user_input)
    expected = session.get_expected_input()
    lower    = user_input.lower()
    logger.info(f"[Session {session.session_id}] Expected={expected!r}, Got={user_input!r}")

    # ─── 1) Resolve which_specific_order ────────────────────────────────────────
    if expected == "which_specific_order":
        orders = session.get_data("specific_orders") or []
        # pick by phrase or index
        if re.search(r"\b(more recent|most recent|recent)\b", lower):
            chosen = orders[0]
        else:
            m = re.search(r"\b(\d+)\b", lower)
            idx = int(m.group(1)) - 1 if m else None
            chosen = orders[idx] if idx is not None and 0 <= idx < len(orders) else None

        if not chosen:
            return _reply(session, "Sorry, I didn't get which one — please say the number or 'the more recent one'.")

        date = _format_date(chosen.get("Order_Date"))
        prod = chosen.get("Product") or chosen.get("Product_Category", "item")
        sales    = chosen.get("Sales", 0.0)
        shipping = chosen.get("Shipping_Cost", 0.0)
        prio     = chosen.get("Order_Priority", "N/A")

        text = (
            f"Your {prod} order on {date} has priority {prio}, costing "
            f"${sales:.2f} plus ${shipping:.2f} shipping."
        )
        session.set_expected_input(None)
        return _reply(session, text)

    # ─── 2) Capture customer_id_for_specific_order ─────────────────────────────
    if expected == "customer_id_for_specific_order":
        m = re.search(r"\b(\d{5})\b", user_input)
        if not m:
            return _reply(session, "I still need your 5‑digit Customer ID to proceed.")
        cid = m.group(1)

        # normalize category
        raw_cat = session.get_data("Device_Type", "")
        category = raw_cat.lower()

        session.set_data("customer_id", cid)
        session.set_expected_input(None)

        all_orders = _fetch_customer_orders(cid)
        if isinstance(all_orders, str):
            return _reply(session, all_orders)

        # try filtering by category, fallback to all if none match
        filtered = [
            o for o in all_orders
            if category in (o.get("Product", "") + " " + o.get("Product_Category", "")).lower()
        ]
        if not filtered:
            filtered = all_orders

        if len(filtered) == 1:
            o = filtered[0]
            date = _format_date(o.get("Order_Date"))
            prod = o.get("Product") or o.get("Product_Category", "item")
            sales    = o.get("Sales", 0.0)
            shipping = o.get("Shipping_Cost", 0.0)
            prio     = o.get("Order_Priority", "N/A")
            text = (
                f"Your {prod} order on {date} has priority {prio}, and cost "
                f"${sales:.2f} plus ${shipping:.2f} shipping."
            )
            return _reply(session, text)

        # multiple orders → list and ask which
        session.set_data("specific_orders", filtered)
        session.set_expected_input("which_specific_order")

        lines = []
        for idx, o in enumerate(filtered, start=1):
            date = _format_date(o.get("Order_Date"))
            prod = o.get("Product") or o.get("Product_Category", "item")
            lines.append(f"{idx}. {date} — {prod}")

        text = (
            f"I found {len(filtered)} {raw_cat} orders for Customer ID {cid}:\n"
            + "\n".join(lines)
            + "\nWhich one would you like details for?"
        )
        return _reply(session, text)

    # ─── 3) Kick off specific‑order flow ────────────────────────────────────────
    m = re.search(r"\bstatus of my (.+?) order\b", lower)
    if m:
        raw_cat = m.group(1)
        session.set_data("order_category", raw_cat)
        session.set_expected_input("customer_id_for_specific_order")
        return _reply(session, f"Please provide your Customer ID to retrieve your {raw_cat} order.")

    # ─── 4) Existing last‑order flow ──────────────────────────────────────────
    if re.search(r"\b(last order|details of my last order)\b", lower):
        session.set_expected_input("customer_id_for_last_order")
        return _reply(session, "Sure—what’s your 5‑digit Customer ID for your last order?")

    if expected == "customer_id_for_last_order":
        m = re.search(r"\b(\d{5})\b", user_input)
        if not m:
            return _reply(session, "I still need your 5‑digit Customer ID.")
        cid = m.group(1)
        session.set_data("customer_id", cid)
        session.set_expected_input(None)

        orders = _fetch_customer_orders(cid)
        if isinstance(orders, str):
            return _reply(session, orders)

        text = chat_handler.generate_order_response({"customer_id": cid, "orders": orders}, "last order")
        return _reply(session, text)

    # ─── 5) High‑priority orders ───────────────────────────────────────────────
    if re.search(r"\b(high[- ]priority|priority orders)\b", lower):
        r = requests.get(f"{ORDER_SERVICE_URL}/data/order-priority/High", timeout=5)
        if r.status_code != 200:
            return _reply(session, r.json().get("error", "No high‑priority orders found."))
        orders = r.json()
        orders = sorted(orders, key=lambda x: x.get("Order_Date",""), reverse=True)[:5]
        text = chat_handler.generate_priority_orders_response(orders, "High")
        return _reply(session, text)

    # ─── 6) Other analytics ────────────────────────────────────────────────────
    if "sales by category" in lower:
        data = requests.get(f"{ORDER_SERVICE_URL}/data/total-sales-by-category", timeout=5).json()
        return _reply(session, chat_handler.generate_sales_by_category(data))
    if "profit by gender" in lower:
        data = requests.get(f"{ORDER_SERVICE_URL}/data/profit-by-gender", timeout=5).json()
        return _reply(session, chat_handler.generate_profit_by_gender(data))
    if any(k in lower for k in ["shipping cost", "shipping summary"]):
        data = requests.get(f"{ORDER_SERVICE_URL}/data/shipping-cost-summary", timeout=5).json()
        return _reply(session, chat_handler.generate_shipping_summary(data))
    if "high profit" in lower:
        data = requests.get(f"{ORDER_SERVICE_URL}/data/high-profit-products", timeout=5).json()
        return _reply(session, chat_handler.generate_high_profit_products(data))

    # ─── 7) Fallback to product search ─────────────────────────────────────────
    try:
        r = requests.post(
            f"{PRODUCT_SERVICE_URL}/search",
            json={"query": user_input, "top_k": 5},
            timeout=5
        )
        r.raise_for_status()
        products = r.json()
        text = chat_handler.generate_product_response(products, user_input)
        return _reply(session, text)
    except Exception as e:
        logger.error(f"Product service error: {e}")
        return _reply(session, "Sorry, I couldn’t reach the product service right now.")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _fetch_customer_orders(customer_id: str):
    try:
        r = requests.get(f"{ORDER_SERVICE_URL}/data/customer/{customer_id}", timeout=5)
        if r.status_code == 404:
            return f"No orders found for Customer ID {customer_id}."
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"Order service error: {e}")
        return "Sorry, I couldn’t fetch your orders at the moment."

def _format_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    except:
        return date_str

def _reply(session: Session, text: str):
    session.add_to_history("bot", text)
    return jsonify({"response": text, "session_id": session.session_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
