# chat_service/intent_classifier.py

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from perplexity_client import PerplexityClient  # your existing client

class IntentClassifier:
    def __init__(self, api_key: str = None, threshold: float = 0.5):
        # Use the same MiniLM model you already have
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.threshold = threshold

        # Define prototypes for each intent
        self.intents = {
            'product_search': [
                'find products',
                'show me',
                'search for',
                'recommend me',
                'what are the top'
            ],
            'last_order': [
                'my last order',
                'most recent order',
                'details of my last purchase',
                'latest purchase'
            ],
            'specific_order': [
                'status of my order',
                'track my order',
                'order status',
                'where is my'
            ],
            'high_priority': [
                'high priority orders',
                'urgent orders',
                'priority orders'
            ],
            'sales_by_category': [
                'sales by category',
                'total sales',
                'how much did we sell'
            ],
            'profit_by_gender': [
                'profit by gender',
                'gender profit'
            ],
            'shipping_summary': [
                'shipping summary',
                'shipping cost summary'
            ],
        }

        # Pre-embed all prototypes
        self.intent_embeddings = {
            intent: self.model.encode(protos, convert_to_tensor=True)
            for intent, protos in self.intents.items()
        }

        # Set up Perplexity for fallback classification
        self.perplexity = PerplexityClient(api_key=api_key) if api_key else None

    def predict(self, query: str) -> str:
        """
        Returns the best-matching intent name for the given user query.
        Falls back to Perplexity classification if top score < threshold.
        """
        q_emb = self.model.encode([query], convert_to_tensor=True)
        # compute max cosine similarity for each intent
        scores = {}
        for intent, emb in self.intent_embeddings.items():
            sim = cosine_similarity(q_emb.cpu(), emb.cpu()).max()
            scores[intent] = float(sim)

        # pick best
        best_intent, best_score = max(scores.items(), key=lambda x: x[1])

        # If uncertain, ask Perplexity
        if best_score < self.threshold and self.perplexity:
            intent_list = list(self.intents.keys())
            prompt = (
                f"Classify this request into one of {intent_list}: \"{query}\""
            )
            try:
                if self.perplexity.api_key is None:
                    raise ValueError("Perplexity API key is missing.")
                result = self.perplexity.search(prompt)
                content = result.get('content', '').lower()
                # map back if possible
                for intent in self.intents:
                    if intent in content:
                        return intent
            except Exception as e:
                print(f"Perplexity API error: {e}")
                # fallback to semantic if Perplexity fails
                pass

        return best_intent
