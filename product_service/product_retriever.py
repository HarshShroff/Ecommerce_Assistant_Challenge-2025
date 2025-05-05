import pandas as pd
import os
import json
from langchain_community.retrievers import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
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

class ProductRetriever:
    def __init__(self):
        self.data_path = os.environ.get('DATA_PATH', '/data/Product_Information_Dataset.csv')
        self.index_path = os.environ.get('FAISS_INDEX_PATH', '/data/faiss_index')
        
        logger.info(f"Loading product data from {self.data_path}")
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
            self.index = FAISS.load_local(self.index_path, self.encoder)
            logger.info("FAISS index loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            logger.info("Creating new FAISS index")
            self._create_index()
    
    def _parse_list(self, text):
        if pd.isna(text):
            return []
        try:
            return json.loads(text.replace("'", "\""))
        except:
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
        # First-stage retrieval
        try:
            docs = self.index.similarity_search(query, k=top_k*2)
            asins = [doc.metadata['asin'] for doc in docs]
            
            # Get candidate products
            candidates = self.df[self.df['parent_asin'].isin(asins)]
            
            # Filter by rating
            candidates = candidates[candidates['average_rating'] >= min_rating]
            
            if candidates.empty:
                logger.warning(f"No products found for query: {query}")
                return []
            
            # Reranking with cross-encoder
            pairs = []
            for _, row in candidates.iterrows():
                title = row['title'] if not pd.isna(row['title']) else ""
                desc = str(row['description']) if not pd.isna(row['description']) else ""
                pairs.append((query, f"{title} {desc}"))
            
            if not pairs:
                return []
                
            scores = self.reranker.predict(pairs)
            
            # Combine with candidates and sort
            candidates_with_scores = list(zip(candidates.iterrows(), scores))
            sorted_candidates = sorted(candidates_with_scores, key=lambda x: x[1], reverse=True)[:top_k]
            
            # Convert to Product objects
            results = []
            for (_, row), _ in sorted_candidates:
                results.append(Product(
                    asin=row['parent_asin'],
                    title=row['title'],
                    price=float(row['price']),
                    rating=float(row['average_rating']),
                    categories=self._parse_list(row['categories']),
                    features=self._parse_list(row['features']),
                    description=str(row['description']) if not pd.isna(row['description']) else None
                ))
            
            return results
        except Exception as e:
            logger.error(f"Error in search: {e}")
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
            description=str(row['description']) if not pd.isna(row['description']) else None
        )
