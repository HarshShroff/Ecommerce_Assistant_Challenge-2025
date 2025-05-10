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
    price: Optional[float] = None
    rating: float
    categories: List[str]
    features: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asin": self.asin,
            "title": self.title,
            "price": self.price if self.price is not None else "N/A",
            "rating": self.rating,
            "categories": self.categories,
            "features": self.features[:3] if self.features else [],
            "description": self.description[:200] + "..." if self.description and len(self.description) > 200 else self.description
        }

class ProductRetriever:
    def __init__(self):
        self.data_path = os.environ.get('DATA_PATH', '/data/Product_Information_Dataset.csv')
        self.index_path = os.environ.get('FAISS_INDEX_PATH', '/data/faiss_index')
        
        logger.info(f"Loading product data from {self.data_path}")
        try:
            self.df = pd.read_csv(self.data_path)
            
            # Clean and preprocess data
            self.df['price'] = pd.to_numeric(self.df['price'], errors='coerce')
            self.df['average_rating'] = pd.to_numeric(self.df['average_rating'], errors='coerce')
            
            # Convert string representations to Python objects
            self.df['categories'] = self.df['categories'].apply(self._parse_list)
            self.df['features'] = self.df['features'].apply(self._parse_list)
            
            # Initialize embeddings and reranker
            logger.info("Initializing embeddings and reranker")
            self.encoder = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            # Load FAISS index
            logger.info(f"Loading FAISS index from {self.index_path}")
            try:
                self.index = FAISS.load_local(self.index_path, self.encoder, allow_dangerous_deserialization=True)
                logger.info("FAISS index loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
                logger.info("Creating new FAISS index")
                self._create_index()
        except Exception as e:
            logger.error(f"Error initializing ProductRetriever: {e}")
            # Initialize empty DataFrame to prevent attribute errors
            self.df = pd.DataFrame()
            self.index = None
    
    def _parse_list(self, text):
        # If it's None, NaN, or an empty value
        if text is None or (isinstance(text, (float, int)) and pd.isna(text)):
            return []
            
        # If it's already a list
        if isinstance(text, list):
            return text
            
        # If it's a string representation of a list
        try:
            return json.loads(text.replace("'", "\""))
        except:
            # If parsing fails, return empty list
            return []
    
    def _create_index(self):
        # Create documents for indexing
        documents = []
        metadatas = []
        
        for _, row in self.df.iterrows():
            title = row['title'] if not pd.isna(row['title']) else ""
            desc = str(row['description']) if not pd.isna(row['description']) else ""
            features = " ".join(self._parse_list(row['features']))
            
            doc_text = f"{title} {desc} {features}"
            documents.append(doc_text)
            
            metadatas.append({"asin": row['parent_asin']})
        
        # Create and save index
        self.index = FAISS.from_texts(documents, self.encoder, metadatas=metadatas)
        os.makedirs(self.index_path, exist_ok=True)
        self.index.save_local(self.index_path)

    def search(self, query: str, top_k=5, min_rating=4.0):
        """
        Perform a semantic + reranked search, falling back to keyword matching.
        """
        try:
            if self.df.empty:
                logger.error("Product DataFrame is empty, cannot perform search")
                return []

            query_lower = query.lower()

            # 1) FAISS semantic search (k×3 candidates)
            logger.info(f"Performing FAISS semantic search for: '{query}'")
            docs = self.index.similarity_search(query, k=top_k * 3)
            asins = [doc.metadata["asin"] for doc in docs]

            # Filter by rating
            candidates = self.df[
                (self.df["parent_asin"].isin(asins)) &
                (self.df["average_rating"] >= min_rating)
            ]

            # 2) Rerank via CrossEncoder
            if not candidates.empty:
                logger.info(f"Reranking {len(candidates)} FAISS candidates")
                titles = candidates["title"].fillna("").tolist()
                pairs  = list(zip([query] * len(titles), titles))
                scores = self.reranker.predict(pairs)
                candidates = candidates.assign(_score=scores)
                candidates = candidates.sort_values("_score", ascending=False).head(top_k)

                return [
                    Product(
                        asin=row["parent_asin"],
                        title=row["title"],
                        price=float(row["price"]),
                        rating=float(row["average_rating"]),
                        categories=self._parse_list(row["categories"]),
                        features=self._parse_list(row["features"]),
                        description=(str(row["description"]) if not pd.isna(row["description"]) else None)
                    ).to_dict()
                    for _, row in candidates.iterrows()
                ]

            # 3) Fallback to simple keyword match in titles
            logger.info("FAISS returned no candidates above rating threshold, falling back to keyword search")
            keywords = query_lower.split()
            results = []
            for _, row in self.df.iterrows():
                title = str(row["title"]).lower() if not pd.isna(row["title"]) else ""
                if all(term in title for term in keywords) and float(row["average_rating"]) >= min_rating:
                    results.append(Product(
                        asin=row["parent_asin"],
                        title=row["title"],
                        price=float(row["price"]),
                        rating=float(row["average_rating"]),
                        categories=self._parse_list(row["categories"]),
                        features=self._parse_list(row["features"]),
                        description=(str(row["description"]) if not pd.isna(row["description"]) else None)
                    ).to_dict())
                    if len(results) >= top_k:
                        break

            logger.info(f"Keyword search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error during dynamic search for '{query}': {e}")
            return []
    
    def get_by_asin(self, asin: str):
        if self.df.empty:
            logger.error("Product DataFrame is empty, cannot get product by ASIN")
            return None
            
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
            description=str(row['description']) if not pd.isna(row['description']) else None
        )
