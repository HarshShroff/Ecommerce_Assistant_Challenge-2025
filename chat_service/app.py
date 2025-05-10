import os
import re
import uuid
import logging
import requests
from datetime import datetime

from flask import Flask, request, jsonify, render_template
from flask_restful import Api, Resource
from flask_cors import CORS
from flasgger import Swagger

from rag_handler import ChatHandler
from session_manager import SessionManager, Session
from intent_classifier import IntentClassifier
from perplexity_client import PerplexityClient

# ────────────────────────────────────────────────────────────────────────────────
# Flask setup
# ────────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
api = Api(app)
swagger = Swagger(app)
CORS(app)  # allow cross‑origin requests from frontend
app.secret_key = os.getenv("FLASK_SECRET_KEY", str(uuid.uuid4()))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Core components
# ────────────────────────────────────────────────────────────────────────────────
CHAT_HANDLER = ChatHandler(perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"))
SESSION_MGR   = SessionManager(session_expiry_seconds=1800)
INTENT_CLS    = IntentClassifier(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    threshold=0.5
)
PERP_CLIENT   = PerplexityClient(api_key=os.getenv("PERPLEXITY_API_KEY"))

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8080")
ORDER_SERVICE_URL   = os.getenv("ORDER_SERVICE_URL",   "http://order-service:8080")

# small‑talk and control keywords
GREETINGS = {"hi","hello","hey","hiya","good morning","good afternoon","good evening"}
FAREWELLS = {"bye","goodbye","see you","farewell"}
THANKS    = {"thanks","thank you","thx","ty"}
CANCELS   = {"cancel","nevermind","never mind","stop"}

# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────
def _format_date(d: str) -> str:
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y")
    except:
        return d

def _fetch_customer_orders(customer_id: str):
    try:
        resp = requests.get(f"{ORDER_SERVICE_URL}/data/customer/{customer_id}", timeout=5)
        if resp.status_code == 404:
            return f"No orders found for Customer ID {customer_id}."
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Order service error: {e}")
        return f"Sorry, I couldn’t fetch your orders right now. Customer ID: {customer_id} not found!"

def _reply(session: Session, text: str, sources=None):
    session.add_to_history("bot", text)
    payload = {"response": text, "session_id": session.session_id}
    if sources:
        payload["sources"] = sources
    return jsonify(payload)

# ────────────────────────────────────────────────────────────────────────────────
# Standard HTTP endpoints
# ────────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    ---
    responses:
      200:
        description: Service is healthy.
    """
    return jsonify({"status": "healthy"})

# ────────────────────────────────────────────────────────────────────────────────
# Chat Resource
# ────────────────────────────────────────────────────────────────────────────────
class Chat(Resource):
    def post(self):
        """
        Handles chat requests.
        """
        body = request.get_json(force=True) or {}
        user_input = (body.get("message") or "").strip()
        if not user_input:
            return jsonify({"error":"Empty message"}), 400

        # session
        sid     = body.get("session_id")
        session: Session = SESSION_MGR.get_session(sid)
        session.add_to_history("user", user_input)

        expected = session.get_expected_input()
        lower    = user_input.lower()
        logger.info(f"[Session {session.session_id}] Expected={expected!r}, Got={user_input!r}")

        # normalize punctuation for small‑talk & commands
        clean = re.sub(r"[^\w\s]","", lower).strip()

        # ─── A) GLOBAL CANCEL ───────────────────────────────────────────────────────
        if clean in CANCELS:
            session.clear()
            return _reply(session, "No problem—let’s start fresh. What can I help with?")

        # ─── B) SMALL‑TALK ───────────────────────────────────────────────────────────
        if expected is None:
            if clean in GREETINGS:
                return _reply(session, "Hello! 👋 I'm your E‑Commerce Assistant. How can I help?")
            if clean in FAREWELLS:
                return _reply(session, "Goodbye! Come back anytime.")
            if clean in THANKS:
                # still enforce any pending slot
                if expected:
                    return _reply(session, "You’re welcome! Now, could you provide that info?")
                return _reply(session, "You’re welcome! Anything else I can do?")

        # ─── C) EVAL‑QUERY: “Is X good for Y?” ────────────────────────────────────────
        eval_match = re.match(
            r"is (?:the )?(?P<prod>.+?) good for (?P<target>.+?)(?:\?|$)",
            lower, flags=re.IGNORECASE
        )
        if eval_match and expected is None:
            keyword = eval_match.group("prod").strip()
            # try product-service first
            candidates = []
            try:
                resp = requests.post(
                    f"{PRODUCT_SERVICE_URL}/search",
                    json={"query": keyword, "top_k": 3},
                    timeout=10
                )
                if resp.status_code == 405:
                    # fallback to GET
                    resp = requests.get(
                        f"{PRODUCT_SERVICE_URL}/search",
                        params={"q": keyword, "top_k": 3},
                        timeout=10
                    )
                resp.raise_for_status()
                candidates = resp.json()
            except Exception as e:
                logger.error(f"Product service error on eval fetch: {e}")

            if candidates:
                # use our RAG handler for a nuanced answer
                answer = CHAT_HANDLER.generate_product_response(candidates, user_input)
                return _reply(session, answer)

            # final fallback: Perplexity
            prompt = f"Is the {keyword} good for {eval_match.group('target').strip()}? Explain why or why not in two sentences."
            perp = PERP_CLIENT.search(prompt) if PERP_CLIENT.api_key else {}
            content = perp.get("content") or (
                f"That device is optimized for speech/video use; it likely won’t capture all the nuances of {eval_match.group('target')}."
            )
            return _reply(session, content, sources=perp.get("sources"))

        # ─── D) SLOT‑FILL FLOWS ──────────────────────────────────────────────────────
        # 1) Which of multiple specific orders?
        if expected == "which_specific_order":
            choices = session.get_data("specific_orders") or []
            if re.search(r"\b(more recent|most recent|recent)\b", lower):
                pick = choices[0] if choices else None
            else:
                m = re.search(r"\b(\d+)\b", lower)
                idx = int(m.group(1))-1 if m else None
                if idx is None or idx<0 or idx>=len(choices):
                    return _reply(session, f"Please choose a number between 1 and {len(choices)} or say 'the more recent one'.")
                pick = choices[idx]
            date     = _format_date(pick["Order_Date"])
            prod     = pick.get("Product") or pick.get("Product_Category","item")
            sales    = pick.get("Sales",0.0)
            shipping = pick.get("Shipping_Cost",0.0)
            prio     = pick.get("Order_Priority","N/A")
            session.set_expected_input(None)
            return _reply(session,
                f"Your {prod} order on {date} has priority {prio}, costing ${sales:.2f} plus ${shipping:.2f} shipping."
            )

        # 2) Customer ID for a specific order status
        if expected == "customer_id_for_specific_order":
            m = re.search(r"\b(\d{5})\b", lower)
            if not m:
                return _reply(session, "I still need your 5‑digit Customer ID to proceed.")
            cid      = m.group(1)
            raw_item = session.get_data("order_item","")
            keyword  = raw_item.replace("-", " ").lower()

            session.set_data("customer_id", cid)
            session.set_expected_input(None)

            orders = _fetch_customer_orders(cid)
            if isinstance(orders, str):
                return _reply(session, orders)

            # filter by normalized keyword tokens
            norm_tokens = keyword.split()
            filtered = [
                o for o in sorted(orders, key=lambda x:x["Order_Date"], reverse=True)
                if all(tok in (o.get("Product","")+" "+o.get("Product_Category","")).lower() for tok in norm_tokens)
            ]
            if not filtered:
                # no match, show most recent few
                filtered = sorted(orders, key=lambda x:x["Order_Date"], reverse=True)[:3]
                lines = [f"{_format_date(o['Order_Date'])} — {o.get('Product') or o.get('Product_Category')}" for o in filtered]
                session.set_expected_input(None)
                return _reply(session,
                    "I couldn’t find exactly that, but here are your most recent orders:\n" +
                    "\n".join(lines)
                )

            if len(filtered) == 1:
                o = filtered[0]
                date = _format_date(o["Order_Date"])
                prod = o.get("Product") or o.get("Product_Category","item")
                prio = o.get("Order_Priority","N/A")
                session.set_expected_input(None)
                return _reply(session,
                    f"You placed an order for {prod} on {date} with priority {prio}. "
                    "If you'd like more info on shipping or delivery, please check your confirmation or contact support."
                )

            # multiple matches → ask which
            session.set_data("specific_orders", filtered)
            session.set_expected_input("which_specific_order")
            lines = [
                f"{i}. {_format_date(o['Order_Date'])} — {o.get('Product') or o.get('Product_Category')}"
                for i,o in enumerate(filtered, start=1)
            ]
            return _reply(session,
                "I found multiple matching orders:\n" +
                "\n".join(lines) +
                "\nWhich one would you like details for?"
            )

        # 3) Customer ID for last-order flow
        if expected == "customer_id_for_last_order":
            m = re.search(r"\b(\d{5})\b", lower)
            if not m:
                return _reply(session, "I still need your 5‑digit Customer ID.")
            cid = m.group(1)
            session.set_data("customer_id", cid)
            session.set_expected_input(None)

            orders = _fetch_customer_orders(cid)
            if isinstance(orders, str):
                return _reply(session, orders)

            text = CHAT_HANDLER.generate_order_response(
                {"customer_id": cid, "orders": orders},
                "last order"
            )
            return _reply(session, text)

        # ─── E) PRICE OVERRIDE → PRODUCT SEARCH ──────────────────────────────────────
        if expected is None and re.search(r"\b(under|over)\s*\$\d+", lower):
            intent = "product_search"
            logger.info(f"[Session {session.session_id}] Price‑query override → product_search")
        else:
            # ─── F) INTENT CLASSIFICATION ──────────────────────────────────────────────
            intent = INTENT_CLS.predict(user_input)
            logger.info(f"[Session {session.session_id}] Detected intent: {intent}")

        # ─── G) ROUTE BASED ON INTENT ────────────────────────────────────────────────
        if intent == "last_order":
            session.set_expected_input("customer_id_for_last_order")
            return _reply(session,
                "Sure—what’s your 5‑digit Customer ID so I can look up your most recent order?"
            )

        if intent == "specific_order":
            m = re.search(
                r"\b(?:status|track|where\s+is|check(?:\s+the)?\s+status)\s+"
                r"(?:of\s+)?(?:my\s+)?(.+?)(?:\s+(?:order|purchase|package))?\b",
                lower
            )
            raw_item = m.group(1).strip() if m else "order"
            session.set_data("order_item", raw_item)
            session.set_expected_input("customer_id_for_specific_order")
            return _reply(session,
                f"Please provide your Customer ID to check the status of your {raw_item} order."
            )

        if intent == "high_priority":
            try:
                resp = requests.get(f"{ORDER_SERVICE_URL}/data/order-priority/High", timeout=5)
                resp.raise_for_status()
                orders = resp.json()
            except Exception as e:
                logger.error(f"High‑priority fetch error: {e}")
                return _reply(session, "I couldn’t fetch high‑priority orders right now.")
            latest5 = sorted(orders, key=lambda x:x["Order_Date"], reverse=True)[:5]
            return _reply(session, CHAT_HANDLER.generate_priority_orders_response(latest5, "High"))

        if intent == "sales_by_category":
            try:
                data = requests.get(f"{ORDER_SERVICE_URL}/data/total-sales-by-category", timeout=5).json()
            except Exception as e:
                logger.error(f"Sales‑by‑category error: {e}")
                return _reply(session, "I couldn’t fetch sales‑by‑category right now.")
            return _reply(session, CHAT_HANDLER.generate_sales_by_category(data))

        if intent == "profit_by_gender":
            try:
                data = requests.get(f"{ORDER_SERVICE_URL}/data/profit-by-gender", timeout=5).json()
            except Exception as e:
                logger.error(f"Profit‑by‑gender error: {e}")
                return _reply(session, "I couldn’t fetch profit‑by‑gender right now.")
            return _reply(session, CHAT_HANDLER.generate_profit_by_gender(data))

        if intent == "shipping_summary":
            try:
                data = requests.get(f"{ORDER_SERVICE_URL}/data/shipping-cost-summary", timeout=5).json()
            except Exception as e:
                logger.error(f"Shipping‑summary error: {e}")
                return _reply(session, "I couldn’t fetch shipping summary right now.")
            return _reply(session, CHAT_HANDLER.generate_shipping_summary(data))

        if intent == "high_profit":
            try:
                data = requests.get(f"{ORDER_SERVICE_URL}/data/high-profit-products", timeout=5).json()
            except Exception as e:
                logger.error(f"High‑profit error: {e}")
                return _reply(session, "I couldn’t fetch high‑profit products right now.")
            return _reply(session, CHAT_HANDLER.generate_high_profit_products(data))

        if intent == "product_search":
            # hit product‑service, with POST→GET fallback
            try:
                resp = requests.post(
                    f"{PRODUCT_SERVICE_URL}/search",
                    json={"query": user_input, "top_k": 5},
                    timeout=10
                )
                if resp.status_code == 405:
                    resp = requests.get(
                        f"{PRODUCT_SERVICE_URL}/search",
                        params={"q": user_input, "top_k": 5},
                        timeout=10
                    )
                resp.raise_for_status()
                prods = resp.json()
                return _reply(session, CHAT_HANDLER.generate_product_response(prods, user_input))
            except Exception as e:
                logger.error(f"Product search error: {e}")
                return _reply(session, "Sorry, I can’t reach the product service right now.")

        # ─── H) FINAL FALLBACK: PERPLEXITY ────────────────────────────────────────────
        try:
            perp = PERP_CLIENT.search(user_input)
            return _reply(session,
                          perp.get("content", "Sorry, I’m not sure how to help."),
                          sources=perp.get("sources"))
        except Exception as e:
            logger.error(f"Perplexity fallback failed: {e}")
            return _reply(session, "Sorry, I’m not sure how to help with that.")

# bind the resource
api.add_resource(Chat, "/chat")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
