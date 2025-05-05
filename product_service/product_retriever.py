import pandas as pd
import os
import json
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sentence_transformers import CrossEncoder
import logging

logger = logging.getLogger(__name__)


class Product(BaseModel):
    asin: str
    title: str
    price: float
    rating: float
    categories: List[str]
    features: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asin": self.asin,
            "title": self.title,
            "price": self.price,
            "rating": self.rating,
            "categories": self.categories,
            "features": self.features[:3] if self.features else [],
            "description": self.description[:200] + "..." if self.description and len(self.description) > 200 else self.description
        }

# product_service/product_retriever.py
# ... (imports and Product class) ...


class ProductRetriever:
    # ... (__init__, _parse_list, _create_index) ...

    def search(self, query: str, top_k=5, min_rating=4.0):
        try:
            query_lower = query.lower()
            exact_phrase_results = []

            # 1. Prioritize exact phrase matches first
            logger.info(f"Searching for exact phrase: '{query_lower}'")
            for _, row in self.df.iterrows():
                title = str(row['title']).lower() if not pd.isna(
                    row['title']) else ""
                # Check for exact phrase and minimum rating
                if query_lower in title and float(row['average_rating']) >= min_rating:
                    try:
                        exact_phrase_results.append(Product(
                            asin=row['parent_asin'],
                            title=row['title'],
                            price=float(row['price']),
                            rating=float(row['average_rating']),
                            categories=self._parse_list(row['categories']),
                            features=self._parse_list(row['features']),
                            description=str(row['description']) if not pd.isna(
                                row['description']) else None
                        ))
                        if len(exact_phrase_results) >= top_k:
                            break
                    except Exception as e:
                        logger.error(
                            f"Error creating product for exact match (ASIN: {row.get('parent_asin', 'N/A')}): {e}")

            if exact_phrase_results:
                logger.info(
                    f"Found {len(exact_phrase_results)} exact phrase matches.")
                return exact_phrase_results

            # 2. If no exact phrase matches, try FAISS semantic search
            logger.info(
                "No exact phrase match found, trying FAISS semantic search.")
            if hasattr(self, 'index') and self.index:
                try:
                    docs = self.index.similarity_search(
                        query, k=top_k * 3)  # Get more candidates
                    asins = [doc.metadata['asin'] for doc in docs]
                    faiss_results_df = self.df[self.df['parent_asin'].isin(
                        asins)]
                    faiss_results_df = faiss_results_df[faiss_results_df['average_rating'] >= min_rating]

                    if not faiss_results_df.empty:
                        # Score based on term overlap (optional refinement)
                        query_terms = query_lower.split()
                        scores = []
                        for _, row in faiss_results_df.iterrows():
                            title = str(row['title']).lower() if not pd.isna(
                                row['title']) else ""
                            score = sum(
                                1 for term in query_terms if term in title)
                            scores.append((row, score))

                        sorted_scores = sorted(
                            scores, key=lambda x: x[1], reverse=True)

                        faiss_processed_results = []
                        for row, _ in sorted_scores[:top_k]:
                            try:
                                faiss_processed_results.append(Product(
                                    asin=row['parent_asin'],
                                    title=row['title'],
                                    price=float(row['price']),
                                    rating=float(row['average_rating']),
                                    categories=self._parse_list(
                                        row['categories']),
                                    features=self._parse_list(row['features']),
                                    description=str(row['description']) if not pd.isna(
                                        row['description']) else None
                                ))
                            except Exception as e:
                                logger.error(
                                    f"Error creating product from FAISS result (ASIN: {row.get('parent_asin', 'N/A')}): {e}")

                        if faiss_processed_results:
                            logger.info(
                                f"Returning {len(faiss_processed_results)} results from FAISS.")
                            return faiss_processed_results

                except Exception as e:
                    logger.warning(
                        f"FAISS search failed: {e}. Falling back to keyword search.")

            # 3. Fallback to keyword search (if FAISS failed or returned nothing)
            logger.info("Falling back to keyword search.")
            query_terms = query_lower.split()
            keyword_results = []

            # Try matching all terms first
            for _, row in self.df.iterrows():
                title = str(row['title']).lower() if not pd.isna(
                    row['title']) else ""
                if all(term in title for term in query_terms) and float(row['average_rating']) >= min_rating:
                    try:
                        keyword_results.append(Product(
                            asin=row['parent_asin'],
                            title=row['title'],
                            price=float(row['price']),
                            rating=float(row['average_rating']),
                            categories=self._parse_list(row['categories']),
                            features=self._parse_list(row['features']),
                            description=None
                        ))
                        if len(keyword_results) >= top_k:
                            break
                    except Exception as e:
                        logger.error(
                            f"Error creating product from keyword match (ASIN: {row.get('parent_asin', 'N/A')}): {e}")

            # If still not enough results, try matching any term
            if len(keyword_results) < top_k:
                logger.info(
                    "Keyword search (all terms) yielded few results, trying partial match.")
                existing_asins = {p.asin for p in keyword_results}
                for _, row in self.df.iterrows():
                    if row['parent_asin'] in existing_asins:
                        continue  # Skip duplicates
                    title = str(row['title']).lower() if not pd.isna(
                        row['title']) else ""
                    if any(term in title for term in query_terms) and float(row['average_rating']) >= min_rating:
                        try:
                            keyword_results.append(Product(
                                asin=row['parent_asin'],
                                title=row['title'],
                                price=float(row['price']),
                                rating=float(row['average_rating']),
                                categories=self._parse_list(row['categories']),
                                features=self._parse_list(row['features']),
                                description=None
                            ))
                            if len(keyword_results) >= top_k:
                                break
                        except Exception as e:
                            logger.error(
                                f"Error creating product from partial keyword match (ASIN: {row.get('parent_asin', 'N/A')}): {e}")

            logger.info(
                f"Returning {len(keyword_results)} results from keyword search.")
            return keyword_results[:top_k]

        except Exception as e:
            logger.error(f"Error during search for query '{query}': {e}")
            return []

    def get_by_asin(self, asin: str):
        product_row = self.df[self.df['parent_asin'] == asin]
        if product_row.empty:
            return None

        row = product_row.iloc[0]
        return Product(
            asin=row['parent_asin'],
            title=row['title'],
            price=float(row['price']),
            rating=float(row['average_rating']),
            categories=self._parse_list(row['categories']),
            features=self._parse_list(row['features']),
            description=str(row['description']) if not pd.isna(
                row['description']) else None
        )
