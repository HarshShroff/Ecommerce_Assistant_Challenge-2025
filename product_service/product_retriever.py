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
        try:
            logger.info(f"Searching for exact phrase: '{query.lower()}'")
            
            # Check if DataFrame is empty
            if self.df.empty:
                logger.error("Product DataFrame is empty, cannot perform search")
                return []
                
            query_lower = query.lower()
            exact_phrase_results = []

            # 1. Prioritize exact phrase matches first
            for _, row in self.df.iterrows():
                title = str(row['title']).lower() if not pd.isna(row['title']) else ""
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
                            description=str(row['description']) if not pd.isna(row['description']) else None
                        ))
                        if len(exact_phrase_results) >= top_k:
                            break
                    except Exception as e:
                        logger.error(f"Error creating product for exact match: {e}")

            if exact_phrase_results:
                logger.info(f"Found {len(exact_phrase_results)} exact phrase matches")
                return exact_phrase_results

            # 2. If no exact phrase matches, try FAISS semantic search
            logger.info("No exact phrase match found, trying FAISS semantic search")
            if hasattr(self, 'index') and self.index:
                try:
                    docs = self.index.similarity_search(query, k=top_k*3)
                    asins = [doc.metadata['asin'] for doc in docs]
                    faiss_results = self.df[self.df['parent_asin'].isin(asins)]
                    faiss_results = faiss_results[faiss_results['average_rating'] >= min_rating]
                    
                    if not faiss_results.empty:
                        # Score based on term overlap
                        query_terms = query_lower.split()
                        scores = []
                        for _, row in faiss_results.iterrows():
                            title = str(row['title']).lower() if not pd.isna(row['title']) else ""
                            score = sum(1 for term in query_terms if term in title)
                            scores.append((row, score))
                        
                        # Sort by score (descending) and take top_k
                        sorted_results = sorted(scores, key=lambda x: x[1], reverse=True)
                        
                        # Convert to Product objects
                        results = []
                        for row, _ in sorted_results[:top_k]:
                            results.append(Product(
                                asin=row['parent_asin'],
                                title=row['title'],
                                price=float(row['price']),
                                rating=float(row['average_rating']),
                                categories=self._parse_list(row['categories']),
                                features=self._parse_list(row['features']),
                                description=str(row['description']) if not pd.isna(row['description']) else None
                            ))
                        
                        if results:
                            logger.info(f"Returning {len(results)} results from FAISS search")
                            return results
                except Exception as e:
                    logger.warning(f"FAISS search failed, falling back to keyword search: {e}")
            
            # 3. Fallback to keyword search
            logger.info("Falling back to keyword search")
            query_terms = query_lower.split()
            results = []
            
            for _, row in self.df.iterrows():
                title = str(row['title']).lower() if not pd.isna(row['title']) else ""
                if any(term in title for term in query_terms) and float(row['average_rating']) >= min_rating:
                    results.append(Product(
                        asin=row['parent_asin'],
                        title=row['title'],
                        price=float(row['price']),
                        rating=float(row['average_rating']),
                        categories=self._parse_list(row['categories']),
                        features=self._parse_list(row['features']),
                        description=None
                    ))
                    if len(results) >= top_k:
                        break
            
            logger.info(f"Returning {len(results)} results from keyword search")
            return results
        except Exception as e:
            logger.error(f"Error during search for query '{query}': {e}")
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
